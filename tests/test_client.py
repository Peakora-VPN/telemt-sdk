import asyncio
import json

import httpx
import pytest

from telemt import (
    APIError,
    AuthenticationError,
    ConflictError,
    InvalidResponseError,
    NotFoundError,
    PermissionDeniedError,
    RequestTimeoutError,
    TelemtClient,
    TransportError,
)
from telemt import (
    models as m,
)

from .conftest import success


async def test_health_and_exact_auth(mock_api):
    client, requests, responses = mock_api
    responses.append(success({"status": "ok", "read_only": False, "new_server_field": 42}))
    result = await client.health.get()
    assert isinstance(result.data, m.HealthData)
    assert result.data.status == "ok"
    assert result.data.model_extra == {"new_server_field": 42}
    assert result.revision == "a" * 64
    assert result.status_code == 200
    assert requests[0].headers["Authorization"] == "exact auth value"
    assert requests[0].headers["Accept"] == "application/json"
    assert requests[0].content == b""


async def test_create_and_nested_user_model(mock_api, user_data):
    client, requests, responses = mock_api
    secret = "ab" * 16
    user_data["links"]["tls_domains"] = [{"domain": "example.com", "link": f"tg://{secret}"}]
    responses.append(success({"user": user_data, "secret": secret}, status=201))
    result = await client.users.create(m.CreateUserRequest(username="alice"), revision="old")
    assert result.data.user.username == "alice"
    assert isinstance(result.data.user.links.tls_domains[0], m.TlsDomainLink)
    assert result.data.secret == secret
    assert secret not in repr(result)
    assert requests[0].headers["If-Match"] == "old"
    assert json.loads(requests[0].content) == {"username": "alice"}


async def test_patch_preserves_omission_null_false_zero(mock_api, user_data):
    client, requests, responses = mock_api
    responses.append(success(user_data, status=202))
    await client.users.update(
        "alice", m.PatchUserRequest(data_quota_bytes=None, enabled=False, max_tcp_conns=0)
    )
    assert json.loads(requests[0].content) == {
        "data_quota_bytes": None,
        "enabled": False,
        "max_tcp_conns": 0,
    }
    assert "If-Match" not in requests[0].headers


async def test_create_user_sparse_body_keeps_omitted_absent_and_sends_explicit_null(
    mock_api, user_data
):
    client, requests, responses = mock_api
    secret = "ab" * 16
    bodies = [
        m.CreateUserRequest(username="alice"),
        m.CreateUserRequest(username="alice", source_deny=None),
        m.CreateUserRequest(username="alice", source_deny=["203.0.113.0/24"], enabled=False),
    ]
    for _ in bodies:
        responses.append(success({"user": user_data, "secret": secret}, status=201))
    for body in bodies:
        await client.users.create(body)
    assert json.loads(requests[0].content) == {"username": "alice"}
    assert json.loads(requests[1].content) == {"username": "alice", "source_deny": None}
    assert json.loads(requests[2].content) == {
        "username": "alice",
        "source_deny": ["203.0.113.0/24"],
        "enabled": False,
    }


async def test_patch_user_source_deny_null_sends_null_and_omission_stays_absent(
    mock_api, user_data
):
    client, requests, responses = mock_api
    responses.extend([success(user_data, status=202), success(user_data, status=202)])
    await client.users.update("alice", m.PatchUserRequest(source_deny=None))
    await client.users.update("alice", m.PatchUserRequest())
    assert json.loads(requests[0].content) == {"source_deny": None}
    assert json.loads(requests[1].content) == {}


async def test_config_reload_query_and_revision(mock_api):
    client, requests, responses = mock_api
    responses.append(
        success(
            {
                "revision": "new",
                "restart_required": True,
                "runtime_reload_required": True,
                "process_restart_required": False,
                "deferred_process_fields": [],
                "changed": ["web"],
                "changed_paths": ["web.enabled"],
                "normalization_effects": [],
            },
            status=202,
            revision="new",
        )
    )
    result = await client.config.update(
        m.PatchConfigRequest(web={"enabled": False}),
        revision='"old"',
        reload=m.ReloadRequest(mode="drain", timeout_secs=30, failure_policy="rollback"),
    )
    assert result.revision == "new"
    assert dict(requests[0].url.params) == {
        "reload": "drain",
        "timeout_secs": "30",
        "failure_policy": "rollback",
    }
    assert requests[0].headers["If-Match"] == '"old"'
    assert json.loads(requests[0].content) == {"web": {"enabled": False}}


def _patch_config_success() -> httpx.Response:
    return success(
        {
            "revision": "new",
            "restart_required": False,
            "runtime_reload_required": True,
            "process_restart_required": False,
            "deferred_process_fields": [],
            "changed": ["web"],
            "changed_paths": ["web.enabled"],
            "normalization_effects": [],
        },
        status=202,
        revision="new",
    )


async def test_config_update_sends_exact_runtime_match_header(mock_api):
    client, requests, responses = mock_api
    responses.append(_patch_config_success())
    token = "abcdef0123456789ABCDEF:0123456789abcdef"
    await client.config.update(m.PatchConfigRequest(web={"enabled": False}), runtime_match=token)
    assert requests[0].headers["If-Runtime-Match"] == token
    assert "If-Match" not in requests[0].headers


async def test_config_update_sends_runtime_match_alongside_if_match(mock_api):
    client, requests, responses = mock_api
    responses.append(_patch_config_success())
    await client.config.update(
        m.PatchConfigRequest(web={"enabled": False}), revision='"old"', runtime_match="ab:cd"
    )
    assert requests[0].headers["If-Match"] == '"old"'
    assert requests[0].headers["If-Runtime-Match"] == "ab:cd"


async def test_config_update_accepts_max_length_runtime_match(mock_api):
    client, requests, responses = mock_api
    responses.append(_patch_config_success())
    token = "ab" * 64
    await client.config.update(m.PatchConfigRequest(web={"enabled": False}), runtime_match=token)
    assert requests[0].headers["If-Runtime-Match"] == token


@pytest.mark.parametrize(
    "token",
    ["", "f" * 129, "not-hex!", "ab:cd:ef:zz", "abcd ef"],
)
async def test_config_update_rejects_invalid_runtime_match_before_transport(mock_api, token):
    client, requests, _ = mock_api
    with pytest.raises(ValueError, match="runtime_match"):
        await client.config.update(
            m.PatchConfigRequest(web={"enabled": False}), runtime_match=token
        )
    assert requests == []


async def test_readiness_503_is_data_but_api_disabled_is_error(mock_api):
    client, _, responses = mock_api
    responses.extend(
        [
            success(
                {
                    "ready": False,
                    "status": "not_ready",
                    "reason": "admission_closed",
                    "admission_open": False,
                    "healthy_upstreams": 0,
                    "total_upstreams": 1,
                },
                status=503,
            ),
            httpx.Response(
                503,
                json={
                    "ok": False,
                    "error": {"code": "api_disabled", "message": "Off"},
                    "request_id": 7,
                },
            ),
        ]
    )
    result = await client.health.ready()
    assert result.status_code == 503 and result.data.ready is False
    with pytest.raises(APIError, match="api_disabled"):
        await client.health.ready()


async def test_closed_session_tombstone(mock_api):
    client, _, responses = mock_api
    ref = "ws1." + "a" * 32 + ".0000000000000001"
    responses.append(
        success(
            {
                "session_ref": ref,
                "state": "closed",
                "attempt": 1,
                "carrier": "https",
                "reason": "operator",
                "closed_age_ms": 10,
            },
            status=410,
        )
    )
    result = await client.runtime.web.session(ref)
    assert isinstance(result.data, m.GoneSessionData)
    assert result.data.closed_age_ms == 10
    assert result.status_code == 410


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (400, APIError),
        (401, AuthenticationError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (409, ConflictError),
        (413, APIError),
        (500, APIError),
    ],
)
async def test_api_errors(mock_api, status, error_type):
    client, requests, responses = mock_api
    responses.append(
        httpx.Response(
            status,
            json={
                "ok": False,
                "error": {"code": "machine_code", "message": "Rejected"},
                "request_id": 9,
            },
        )
    )
    with pytest.raises(error_type) as caught:
        await client.users.delete("alice")
    assert caught.value.code == "machine_code"
    assert caught.value.message == "Rejected"
    assert caught.value.request_id == 9
    assert caught.value.status_code == status
    assert caught.value.details == ()
    assert len(requests) == 1


async def test_error_details_propagate_to_api_error(mock_api):
    client, _, responses = mock_api
    responses.append(
        httpx.Response(
            400,
            json={
                "ok": False,
                "error": {
                    "code": "invalid_fields",
                    "message": "Rejected",
                    "details": [
                        {
                            "path": "network.dns_overrides",
                            "code": "invalid_entry",
                            "message": "bad",
                        },
                        {"path": "web.enabled", "code": "read_only", "message": "locked"},
                    ],
                },
                "request_id": 11,
            },
        )
    )
    with pytest.raises(APIError) as caught:
        await client.config.update(m.PatchConfigRequest(web={"enabled": False}))
    assert caught.value.code == "invalid_fields"
    assert caught.value.request_id == 11
    details = caught.value.details
    assert [issue.path for issue in details] == ["network.dns_overrides", "web.enabled"]
    assert [issue.code for issue in details] == ["invalid_entry", "read_only"]
    assert [issue.message for issue in details] == ["bad", "locked"]
    assert all(isinstance(issue, m.FieldIssue) for issue in details)


@pytest.mark.parametrize(
    "body",
    [
        b"<html>Bad gateway</html>",
        b"[]",
        b"null",
        b"{}",
        b'{"ok": 1}',
        b'{"ok": false, "error": {}}',
        b'{"ok": true, "data": {}, "revision": "a"}',
        b'{"ok": true, "data": {"status": "ok", "read_only": "false"}, "revision": "a"}',
    ],
)
async def test_invalid_response(mock_api, body):
    client, _, responses = mock_api
    responses.append(httpx.Response(200, content=body))
    with pytest.raises(InvalidResponseError) as caught:
        await client.health.get()
    assert caught.value.status_code == 200


async def test_error_status_with_success_envelope_is_not_silently_accepted(mock_api):
    client, _, responses = mock_api
    responses.append(success({"status": "ok", "read_only": False}, status=500))
    with pytest.raises(APIError, match="unexpected_http_status"):
        await client.health.get()


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        (httpx.ReadTimeout("timeout"), RequestTimeoutError),
        (httpx.ConnectError("offline"), TransportError),
    ],
)
async def test_transport_errors_are_not_retried(original, expected):
    requests = []

    def handler(request):
        requests.append(request)
        raise original

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with TelemtClient("https://telemt.example", http_client=http) as client:
            with pytest.raises(expected) as caught:
                await client.users.delete("alice")
            assert caught.value.__cause__ is original
    assert len(requests) == 1


async def test_cancellation_propagates():
    async def handler(request):
        raise asyncio.CancelledError

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with TelemtClient("http://localhost", http_client=http) as client:
            with pytest.raises(asyncio.CancelledError):
                await client.health.get()


async def test_owned_and_borrowed_client_lifecycle():
    client = TelemtClient("http://localhost")
    async with client:
        assert not client._http.is_closed
    assert client._http.is_closed
    await client.aclose()
    with pytest.raises(RuntimeError, match="closed"):
        await client.health.get()
    with pytest.raises(RuntimeError, match="closed"):
        await client.__aenter__()
    async with httpx.AsyncClient() as http:
        async with TelemtClient("http://localhost", http_client=http):
            pass
        assert not http.is_closed


@pytest.mark.parametrize(
    ("url", "path"),
    [
        ("http://localhost:9091", "/v1/health"),
        ("http://localhost:9091/", "/v1/health"),
        ("http://localhost:9091/v1/", "/v1/health"),
        ("http://localhost:9091/proxy", "/proxy/v1/health"),
    ],
)
async def test_base_url_and_timeout(url, path):
    def handler(request):
        assert request.url.path == path
        assert request.extensions["timeout"]["read"] == 2.0
        assert "Authorization" not in request.headers
        return success({"status": "ok", "read_only": False})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with TelemtClient(url, timeout=2.0, http_client=http) as client:
            await client.health.get()


@pytest.mark.parametrize(
    "url",
    [
        "localhost:9091",
        "/v1",
        "ftp://localhost",
        "http://u:p@localhost",
        "http://localhost?q=1",
        "http://localhost#x",
    ],
)
def test_invalid_base_url(url):
    with pytest.raises(ValueError):
        TelemtClient(url)


async def test_redirects_are_not_followed():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(307, headers={"Location": "https://another.example/"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as http:
        async with TelemtClient(
            "http://localhost", auth_header="secret", http_client=http
        ) as client:
            with pytest.raises(InvalidResponseError):
                await client.health.get()
    assert len(requests) == 1


async def test_concurrent_requests_keep_independent_revisions(user_data):
    async def handler(request):
        name = request.url.path.rsplit("/", 1)[1]
        await asyncio.sleep(0)
        return success({**user_data, "username": name}, revision=name)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with TelemtClient("http://localhost", http_client=http) as client:
            first, second = await asyncio.gather(client.users.get("alice"), client.users.get("bob"))
    assert first.revision == first.data.username == "alice"
    assert second.revision == second.data.username == "bob"


def _operation_status(state):
    return {
        "operation_id": f"wo1.{'a' * 32}.0000000000000001",
        "state": state,
        "requested": 1,
        "scanned": 1,
        "matched": 1,
        "close_signalled": 0,
        "conflicted": 0,
        "created_epoch_millis": 1_700_000_000_000,
        "updated_epoch_millis": 1_700_000_000_001,
    }


async def test_wait_operation_returns_cancelled_result(mock_api):
    # cancelled is terminal for WEB operations: return it instead of polling forever.
    client, requests, responses = mock_api
    responses.append(success(_operation_status("cancelled")))
    result = await client.runtime.web.wait_operation(
        f"wo1.{'a' * 32}.0000000000000001", timeout=5, poll_interval=0.01
    )
    assert result.data.state == "cancelled"
    assert len(requests) == 1


async def test_wait_operation_returns_completed_result(mock_api):
    client, requests, responses = mock_api
    responses.append(success(_operation_status("completed")))
    result = await client.runtime.web.wait_operation(
        f"wo1.{'a' * 32}.0000000000000001", timeout=5, poll_interval=0.01
    )
    assert result.data.state == "completed"
    assert len(requests) == 1
