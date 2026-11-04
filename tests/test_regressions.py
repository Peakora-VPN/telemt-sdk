import json
import traceback

import httpx
import pytest
from pydantic import ValidationError

from telemt import InvalidResponseError, TelemtClient
from telemt import models as m


@pytest.mark.parametrize(
    "value",
    [
        "2026-01-01T10:00Z",
        "2026-01-01T10:00:00+0300",
        "2026-01-01T10:00:00+03:00:30",
        "2026-01-01T10:00:00,123Z",
        "2026-02-29T00:00:00Z",
        "2026-01-01T24:00:00Z",
        "2026-01-01T10:00:61Z",
        "2026-01-01T10:00:00+00:60",
        "2026-01-01T10:00:00Z\n",
    ],
)
def test_expiration_rejects_iso8601_extensions_and_invalid_dates(value):
    with pytest.raises(ValidationError):
        m.PatchUserRequest(expiration_rfc3339=value)


@pytest.mark.parametrize(
    "value",
    [
        "2028-02-29T10:00:00Z",
        "2026-01-01t10:00:00z",
        "2026-01-01 10:00:00+03:00",
        "2016-12-31T23:59:60Z",
        "0000-01-01T00:00:00Z",
        "2026-01-01T10:00:00.123456789Z",
    ],
)
def test_expiration_accepts_chrono_rfc3339_without_losing_precision(value):
    assert m.PatchUserRequest(expiration_rfc3339=value).expiration_rfc3339 == value


def test_mapped_ipv6_matches_rust_display():
    assert m.SessionQuery(ip="::ffff:192.0.2.1").ip == "::ffff:192.0.2.1"
    with pytest.raises(ValidationError):
        m.SessionQuery(ip="::ffff:c000:201")


def test_null_secret_is_noop_not_removal():
    assert m.PatchUserRequest(secret=None).model_dump(exclude_unset=True) == {"secret": None}


@pytest.mark.parametrize("method", ["session", "operation"])
async def test_zero_runtime_reference_is_rejected(mock_api, method):
    client, requests, _ = mock_api
    prefix = "ws1" if method == "session" else "wo1"
    with pytest.raises(ValidationError):
        await getattr(client.runtime.web, method)(f"{prefix}.{'a' * 32}.0000000000000000")
    assert not requests


async def test_unsigned_reload_id_bound(mock_api):
    client, requests, _ = mock_api
    with pytest.raises(ValueError):
        await client.system.reload_status(2**64)
    assert not requests


async def test_mutated_body_revalidated_before_sending(mock_api):
    client, requests, _ = mock_api
    request = m.CloseRequest(
        runtime_instance="a" * 32,
        selector=m.RefsSelector(session_refs=[f"ws1.{'a' * 32}.0000000000000001"]),
    )
    request.selector.session_refs.clear()
    with pytest.raises(ValidationError):
        await client.runtime.web.close_sessions(request)
    assert not requests


async def test_mutated_queries_revalidated_before_sending(mock_api):
    client, requests, _ = mock_api
    query = m.SessionQuery(limit=20)
    query.limit = 0
    with pytest.raises(ValidationError):
        await client.runtime.web.sessions(query)
    reload = m.ReloadRequest()
    reload.mode = "drain"
    with pytest.raises(ValidationError):
        await client.config.update(m.PatchConfigRequest(web={"enabled": True}), reload=reload)
    assert not requests


async def test_invalid_secret_is_not_in_exception_traceback(mock_api):
    client, _, responses = mock_api
    secret = "sensitive-test-value"
    responses.append(
        httpx.Response(
            201,
            json={
                "ok": True,
                "revision": "r",
                "data": {"user": secret, "secret": secret},
            },
        )
    )
    with pytest.raises(InvalidResponseError) as caught:
        await client.users.create(m.CreateUserRequest(username="alice"))
    assert secret not in "".join(traceback.format_exception(caught.value))


async def test_borrowed_http_client_does_not_override_protocol():
    def handler(request):
        assert request.url.query == b""
        assert request.headers.get_list("Content-Type") == ["application/json"]
        assert request.headers["Authorization"] == "exact auth"
        assert json.loads(request.content) == {"runtime_instance": "a" * 32}
        return httpx.Response(
            200,
            json={
                "ok": True,
                "revision": "r",
                "data": {
                    "runtime_instance": "a" * 32,
                    "records_cleared": 0,
                    "leased_bytes": 0,
                    "epoch": 1,
                },
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        params={"unexpected": "query"},
        headers={"Content-Type": "text/plain"},
        auth=("unexpected", "basic-auth"),
    ) as http:
        async with TelemtClient(
            "http://localhost", auth_header="exact auth", http_client=http
        ) as client:
            await client.runtime.web.clear_debug(
                m.RuntimeInstanceRequest(runtime_instance="a" * 32)
            )


async def test_me_selftest_nullable_bind_and_typed_upstreams(mock_api):
    client, _, responses = mock_api
    responses.append(
        httpx.Response(
            200,
            json={
                "ok": True,
                "revision": "r",
                "data": {
                    "enabled": True,
                    "generated_at_epoch_secs": 1,
                    "data": {
                        "kdf": {
                            "state": "ok",
                            "ewma_errors_per_min": 0.0,
                            "threshold_errors_per_min": 1.0,
                            "errors_total": 0,
                        },
                        "timeskew": {"state": "unknown", "samples_15m": 0},
                        "ip": {"v4": {"addr": "192.0.2.1", "state": "ok"}},
                        "pid": {"pid": 1, "state": "ok"},
                        "bnd": None,
                        "upstreams": [
                            {
                                "upstream_id": 0,
                                "route_kind": "direct",
                                "address": "direct",
                                "bnd": None,
                                "ip": "192.0.2.1",
                            }
                        ],
                    },
                },
            },
        )
    )
    payload = (await client.runtime.me_selftest()).data.data
    assert payload.bnd is None
    assert isinstance(payload.upstreams[0], m.RuntimeMeSelftestUpstreamData)
    assert payload.upstreams[0].ip == "192.0.2.1"
