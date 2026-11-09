import json

import httpx
import pytest

from telemt import AuthenticationError
from telemt import models as m

from .conftest import success

INSTANCE = "a" * 32
SESSION = f"ws1.{INSTANCE}.0000000000000001"
OPERATION = f"wo1.{INSTANCE}.0000000000000001"

# Independent inventory of the 54 routes in the upstream endpoint matrix.
READ_ROUTES = [
    ("health.get", "health", ()),
    ("health.ready", "health/ready", ()),
    ("system.info", "system/info", ()),
    ("system.reload_status", "system/reload/7", (7,)),
    ("limits.effective", "limits/effective", ()),
    ("security.posture", "security/posture", ()),
    ("security.whitelist", "security/whitelist", ()),
    ("stats.summary", "stats/summary", ()),
    ("stats.zero_all", "stats/zero/all", ()),
    ("stats.upstreams", "stats/upstreams", ()),
    ("stats.minimal_all", "stats/minimal/all", ()),
    ("stats.me_writers", "stats/me-writers", ()),
    ("stats.dcs", "stats/dcs", ()),
    ("stats.active_ips", "stats/users/active-ips", ()),
    ("stats.users", "stats/users", ()),
    ("stats.quota", "stats/users/quota", ()),
    ("runtime.gates", "runtime/gates", ()),
    ("runtime.initialization", "runtime/initialization", ()),
    ("runtime.me_pool_state", "runtime/me_pool_state", ()),
    ("runtime.me_quality", "runtime/me_quality", ()),
    ("runtime.upstream_quality", "runtime/upstream_quality", ()),
    ("runtime.nat_stun", "runtime/nat_stun", ()),
    ("runtime.me_selftest", "runtime/me-selftest", ()),
    ("runtime.connections_summary", "runtime/connections/summary", ()),
    ("runtime.events_recent", "runtime/events/recent", ()),
    ("runtime.tls_fingerprints", "runtime/tls-fingerprints", ()),
    ("runtime.web.status", "runtime/web/status", ()),
    ("runtime.web.sessions", "runtime/web/sessions", ()),
    ("runtime.web.session", f"runtime/web/sessions/{SESSION}", (SESSION,)),
    ("runtime.web.operation", f"runtime/web/operations/{OPERATION}", (OPERATION,)),
    ("config.get", "config", ()),
    ("config.schema", "config/schema", ()),
    ("config.state", "config/state", ()),
    ("discovery.capabilities", "capabilities", ()),
    ("access.get", "access/policy", ()),
    ("users.list", "users", ()),
    ("users.get", "users/alice", ("alice",)),
]

WRITE_ROUTES = [
    (
        "users.create",
        "POST",
        "users",
        (m.CreateUserRequest(username="alice"),),
        {"username": "alice"},
    ),
    (
        "users.update",
        "PATCH",
        "users/alice",
        ("alice", m.PatchUserRequest(enabled=None)),
        {"enabled": None},
    ),
    ("users.delete", "DELETE", "users/alice", ("alice",), None),
    ("users.rotate_secret", "POST", "users/alice/rotate-secret", ("alice",), None),
    ("users.enable", "POST", "users/alice/enable", ("alice",), None),
    ("users.disable", "POST", "users/alice/disable", ("alice",), None),
    ("users.reset_quota", "POST", "users/alice/reset-quota", ("alice",), None),
    (
        "config.update",
        "PATCH",
        "config",
        (m.PatchConfigRequest(general={"fast_mode": True}),),
        {"general": {"fast_mode": True}},
    ),
    (
        "config.update",
        "PATCH",
        "config",
        (m.PatchConfigRequest(network={"dns_overrides": ["upstream.example:443:192.0.2.10"]}),),
        {"network": {"dns_overrides": ["upstream.example:443:192.0.2.10"]}},
    ),
    (
        "config.update",
        "PATCH",
        "config",
        (
            m.PatchConfigRequest(
                server={"api": {"runtime_edge_enabled": True, "runtime_edge_cache_ttl_ms": 0}}
            ),
        ),
        {"server": {"api": {"runtime_edge_enabled": True, "runtime_edge_cache_ttl_ms": 0}}},
    ),
    (
        "config.validate",
        "POST",
        "config/validate",
        (m.PatchConfigRequest(general={"fast_mode": True}),),
        {"general": {"fast_mode": True}},
    ),
    (
        "access.update",
        "PATCH",
        "access/policy",
        (m.AccessPolicyPatch(user_max_tcp_conns_global_each=None),),
        {"user_max_tcp_conns_global_each": None},
    ),
    ("system.reload", "POST", "system/reload", (), None),
    (
        "runtime.web.close_sessions",
        "POST",
        "runtime/web/sessions/close",
        (
            m.CloseRequest(
                runtime_instance=INSTANCE, selector=m.RefsSelector(session_refs=[SESSION])
            ),
        ),
        {"runtime_instance": INSTANCE, "selector": {"kind": "refs", "session_refs": [SESSION]}},
    ),
    (
        "runtime.web.clear_debug",
        "POST",
        "runtime/web/debug/clear",
        (m.RuntimeInstanceRequest(runtime_instance=INSTANCE),),
        {"runtime_instance": INSTANCE},
    ),
    (
        "runtime.web.reset_carrier_learning",
        "POST",
        "runtime/web/carrier-learning/reset",
        (m.RuntimeInstanceRequest(runtime_instance=INSTANCE),),
        {"runtime_instance": INSTANCE},
    ),
    (
        "runtime.web.pause",
        "POST",
        "runtime/web/lifecycle/pause",
        (m.RuntimeInstanceRequest(runtime_instance=INSTANCE),),
        {"runtime_instance": INSTANCE},
    ),
    (
        "runtime.web.drain",
        "POST",
        "runtime/web/lifecycle/drain",
        (m.DrainRequest(runtime_instance=INSTANCE, timeout_secs=30),),
        {"runtime_instance": INSTANCE, "timeout_secs": 30},
    ),
    (
        "runtime.web.resume",
        "POST",
        "runtime/web/lifecycle/resume",
        (m.RuntimeInstanceRequest(runtime_instance=INSTANCE),),
        {"runtime_instance": INSTANCE},
    ),
]


def resolve(client, method):
    for name in method.split("."):
        client = getattr(client, name)
    return client


def unauthorized():
    return httpx.Response(
        401,
        json={"ok": False, "error": {"code": "unauthorized", "message": "Denied"}, "request_id": 1},
    )


@pytest.mark.parametrize(("method", "path", "args"), READ_ROUTES)
async def test_read_route(mock_api, method, path, args):
    client, requests, responses = mock_api
    responses.append(unauthorized())
    with pytest.raises(AuthenticationError):
        await resolve(client, method)(*args)
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].url.path == "/v1/" + path
    assert requests[0].url.query == b""
    assert requests[0].content == b""


@pytest.mark.parametrize(("method", "verb", "path", "args", "body"), WRITE_ROUTES)
async def test_write_route(mock_api, method, verb, path, args, body):
    client, requests, responses = mock_api
    responses.append(unauthorized())
    kwargs = {} if method.startswith("runtime.web") else {"revision": "expected-revision"}
    with pytest.raises(AuthenticationError):
        await resolve(client, method)(*args, **kwargs)
    request = requests[0]
    assert request.method == verb
    assert request.url.path == "/v1/" + path
    assert request.url.query == b""
    if body is None:
        assert request.content == b""
    else:
        assert json.loads(request.content) == body
        assert request.headers.get_list("Content-Type") == ["application/json"]
    if kwargs:
        assert request.headers["If-Match"] == "expected-revision"


@pytest.mark.parametrize("method", ["runtime.events_recent", "runtime.tls_fingerprints"])
async def test_limit_query(mock_api, method):
    client, requests, responses = mock_api
    responses.append(unauthorized())
    with pytest.raises(AuthenticationError):
        await resolve(client, method)(limit=100)
    assert dict(requests[0].url.params) == {"limit": "100"}


async def test_session_query(mock_api):
    client, requests, responses = mock_api
    responses.append(
        success(
            {
                "sessions": [],
                "next_cursor": None,
                "scan_truncated": False,
                "scanned": 0,
                "partial_sessions": 0,
                "partial": [],
            }
        )
    )
    result = await client.runtime.web.sessions(
        m.SessionQuery(limit=10, user="alice", cursor=SESSION)
    )
    assert result.data.sessions == []
    assert dict(requests[0].url.params) == {"limit": "10", "user": "alice", "cursor": SESSION}


async def test_nested_telemetry_and_disabled_payload(mock_api):
    client, _, responses = mock_api
    responses.extend(
        [
            success(
                {
                    "uptime_seconds": 1.5,
                    "connections_total": 3,
                    "connections_bad_total": 1,
                    "connections_bad_by_class": [{"class": "tls", "total": 1}],
                    "handshake_failures_by_class": [],
                    "handshake_timeouts_total": 0,
                    "configured_users": 2,
                }
            ),
            success(
                {
                    "enabled": False,
                    "reason": "feature_disabled",
                    "generated_at_epoch_secs": 1,
                    "data": None,
                }
            ),
        ]
    )
    summary = await client.stats.summary()
    assert summary.data.connections_bad_by_class[0].class_ == "tls"
    assert summary.data.model_dump(by_alias=True)["connections_bad_by_class"][0]["class"] == "tls"
    disabled = await client.runtime.me_quality()
    assert disabled.data.data is None
    assert disabled.data.reason == "feature_disabled"


@pytest.mark.parametrize("username", ["", ".", "..", "../config", "a/b", "a?x=1", "a#x", "a%2fb"])
async def test_unsafe_username_rejected_before_transport(mock_api, username):
    client, requests, _ = mock_api
    with pytest.raises(ValueError):
        await client.users.delete(username)
    assert requests == []


@pytest.mark.parametrize("value", [0, 1001, -1, True, "10"])
async def test_invalid_limit(mock_api, value):
    client, requests, _ = mock_api
    with pytest.raises(ValueError):
        await client.runtime.events_recent(limit=value)
    assert not requests


@pytest.mark.parametrize("value", ["../../config", "", "wo1.wrong.id", 1])
async def test_invalid_reference(mock_api, value):
    client, requests, _ = mock_api
    with pytest.raises(ValueError):
        await client.runtime.web.operation(value)
    assert not requests


@pytest.mark.parametrize("value", [-1, True, "1"])
async def test_invalid_reload_id(mock_api, value):
    client, requests, _ = mock_api
    with pytest.raises(ValueError):
        await client.system.reload_status(value)
    assert not requests


def _comparison(status="published_match"):
    return {
        "scope": "selected_sections",
        "status": status,
        "pending_paths": [],
        "watcher_pending_paths": [],
        "generation_pending_paths": [],
        "process_deferred_paths": [],
        "deferred_process_fields": [],
        "runtime_derived_paths": [],
        "truncated": False,
    }


def _busy_state_data(sections=("general", "network")):
    return {
        "scope": "published_configuration_not_subsystem_acknowledgment",
        "sections": list(sections),
        "runtime": {
            "active_generation": 7,
            "config_epoch": 42,
            "runtime_match": "ab" * 16 + ":7:42",
        },
        "runtime_sample_current": False,
        "desired_revision": None,
        "desired_status": "busy",
        "desired_error": {"path": "$", "code": "config_state_busy", "message": "occupied"},
        "desired": None,
        "effective": None,
        "projection_error": None,
        "comparison": _comparison(status="unknown"),
        "watcher": None,
        "watcher_matches_desired": None,
        "reload": None,
        "reload_observation": "busy",
        "reload_matches_desired": None,
        "subsystem_convergence": "unknown",
    }


async def test_state_sections_serialize_as_one_query_value(mock_api):
    client, requests, responses = mock_api
    responses.append(success(_busy_state_data(), revision=None))
    result = await client.config.state(sections=["general", "network"])
    assert dict(requests[0].url.params) == {"sections": "general,network"}
    assert result.revision is None
    assert result.data.desired_status == "busy"


@pytest.mark.parametrize(
    "sections",
    [
        [],
        (),
        ["general", "general"],
        ("network", "general", "network"),
        ["bogus"],
        ["general", "bogus"],
        "general",
        ["general", 1],
    ],
)
async def test_state_sections_rejected_before_transport(mock_api, sections):
    client, requests, _ = mock_api
    with pytest.raises(ValueError, match="sections"):
        await client.config.state(sections=sections)
    assert requests == []


def _validation_data():
    return {
        "valid": True,
        "base_revision": "11" * 32,
        "candidate_revision": "22" * 32,
        "runtime": {
            "active_generation": 7,
            "config_epoch": 42,
            "runtime_match": "ab" * 16 + ":7:42",
        },
        "changed_paths": ["network.dns_overrides"],
        "normalization_effects": [
            {"path": "upstreams[0].bindtodevice", "code": "alias_canonicalized"}
        ],
        "apply": {
            "watcher_paths": ["network.dns_overrides"],
            "generation_paths": [],
            "process_restart_paths": [],
            "restart_required": False,
            "runtime_reload_required": True,
            "process_restart_required": False,
            "deferred_process_fields": [],
        },
        "source_ownership": "single_source",
        "touched_sections": ["network"],
        "reload": {"mode": "instant", "failure_policy": "keep_new"},
        "warnings": [
            {
                "path": "$",
                "code": "reload_not_requested",
                "message": "Generation-owned changes require an explicit reload",
            }
        ],
    }


async def test_config_validate_reload_query_and_preconditions(mock_api):
    client, requests, responses = mock_api
    responses.append(success(_validation_data(), revision="11" * 32))
    result = await client.config.validate(
        m.PatchConfigRequest(network={"dns_overrides": ["upstream.example:443:192.0.2.10"]}),
        revision='"old"',
        runtime_match="ab:cd",
        reload=m.ReloadRequest(mode="drain", timeout_secs=30, failure_policy="rollback"),
    )
    assert result.data.valid is True
    assert result.revision == "11" * 32
    assert dict(requests[0].url.params) == {
        "reload": "drain",
        "timeout_secs": "30",
        "failure_policy": "rollback",
    }
    assert requests[0].headers["If-Match"] == '"old"'
    assert requests[0].headers["If-Runtime-Match"] == "ab:cd"
    assert json.loads(requests[0].content) == {
        "network": {"dns_overrides": ["upstream.example:443:192.0.2.10"]}
    }


def _policy(**overrides):
    policy = {
        "user_max_tcp_conns_global_each": 12,
        "user_max_unique_ips_global_each": 8,
        "user_max_unique_ips_mode": "active_window",
        "user_max_unique_ips_window_secs": 300,
        "cidr_rate_limits": {
            "192.0.2.0/24": {"up_bps": 8_000_000, "down_bps": 16_000_000},
        },
    }
    policy.update(overrides)
    return policy


def _access_policy_data(**overrides):
    data = {
        "desired": _policy(),
        "effective": _policy(),
        "runtime": {
            "active_generation": 7,
            "config_epoch": 42,
            "runtime_match": "ab" * 16 + ":7:42",
        },
        "published_match": True,
        "effective_scope": "active_config_snapshot",
        "subsystem_convergence": "unknown",
        "apply_mode": "watcher",
    }
    data.update(overrides)
    return data


async def test_access_update_sends_both_preconditions(mock_api):
    client, requests, responses = mock_api
    responses.append(
        success(
            _access_policy_data(changed_paths=["access.user_max_tcp_conns_global_each"]),
            revision="cd" * 32,
        )
    )
    result = await client.access.update(
        m.AccessPolicyPatch(user_max_tcp_conns_global_each=8),
        revision='"old"',
        runtime_match="ab:cd",
    )
    assert result.data.changed_paths == ["access.user_max_tcp_conns_global_each"]
    assert requests[0].headers["If-Match"] == '"old"'
    assert requests[0].headers["If-Runtime-Match"] == "ab:cd"
    assert json.loads(requests[0].content) == {"user_max_tcp_conns_global_each": 8}


async def test_access_update_rejects_invalid_runtime_match_before_transport(mock_api):
    client, requests, _ = mock_api
    with pytest.raises(ValueError, match="runtime_match"):
        await client.access.update(
            m.AccessPolicyPatch(user_max_tcp_conns_global_each=8), runtime_match="not-hex!"
        )
    assert requests == []
