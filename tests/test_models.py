import pytest
from pydantic import ValidationError

from telemt import models as m

INSTANCE = "a" * 32
SESSION = f"ws1.{INSTANCE}.0000000000000001"


@pytest.mark.parametrize(
    ("model", "values"),
    [
        (m.CreateUserRequest, {"username": "a/b"}),
        (m.CreateUserRequest, {"username": "a", "secret": "short"}),
        (m.CreateUserRequest, {"username": "a", "quota_period": "daily"}),
        (m.CreateUserRequest, {"username": "a", "unknown": 1}),
        (m.PatchUserRequest, {"max_tcp_conns": -1}),
        (m.PatchUserRequest, {"data_quota_bytes": 2**64}),
        (m.PatchUserRequest, {"max_tcp_conns": True}),
        (m.PatchUserRequest, {"enabled": "false"}),
        (m.PatchUserRequest, {"expiration_rfc3339": "2026-11-04"}),
        (m.PatchUserRequest, {"expiration_rfc3339": "not-a-date"}),
        (m.CreateUserRequest, {"username": "a", "source_deny": "203.0.113.0/24"}),
        (m.CreateUserRequest, {"username": "a", "source_deny": ["not-a-cidr"]}),
        (m.CreateUserRequest, {"username": "a", "source_deny": ["192.0.2.1"]}),
        (m.CreateUserRequest, {"username": "a", "source_deny": ["192.0.2.0/33"]}),
        (m.CreateUserRequest, {"username": "a", "source_deny": ["fe80::1%eth0/10"]}),
        (m.PatchUserRequest, {"source_deny": [""]}),
        (m.AccessPolicyPatch, {}),
        (m.AccessPolicyPatch, {"user_max_tcp_conns_global_each": -1}),
        (m.AccessPolicyPatch, {"user_max_unique_ips_global_each": -1}),
        (m.AccessPolicyPatch, {"user_max_unique_ips_mode": "sliding_window"}),
        (m.AccessPolicyPatch, {"user_max_unique_ips_window_secs": 0}),
        (m.AccessPolicyPatch, {"user_max_unique_ips_window_secs": -5}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"not-a-cidr": {"up_bps": 1}}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"*4/33": {"up_bps": 1}}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"*6/129": {"up_bps": 1}}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"*/33": {"up_bps": 1}}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"*5/24": {"up_bps": 1}}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"*4/x": {"up_bps": 1}}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"192.0.2.0/24": {"up_bps": 100_000_000_001}}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"192.0.2.0/24": {"up_bps": -1}}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"192.0.2.0/24": True}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"192.0.2.0/24": {"up_bps": 1, "junk": 2}}}),
        (m.AccessPolicyPatch, {"cidr_rate_limits": {"192.0.2.0/24": {}}}),
        (m.AccessPolicyPatch, {"user_max_tcp_conns_global_each": 1, "unexpected": 2}),
        (m.PatchConfigRequest, {}),
        (m.PatchConfigRequest, {"general": None}),
        (m.PatchConfigRequest, {"access": {}}),
        (m.PatchConfigRequest, {"server": {"api": {}}}),
        (m.PatchConfigRequest, {"server": {}}),
        (m.PatchConfigRequest, {"network": {}}),
        (m.PatchConfigRequest, {"network": {"bind": "0.0.0.0"}}),
        (m.PatchConfigRequest, {"network": {"bind": None}}),
        (m.PatchConfigRequest, {"network": {"dns_overrides": None}}),
        (m.PatchConfigRequest, {"server": {"port": 443}}),
        (m.PatchConfigRequest, {"server": {"port": None}}),
        (m.PatchConfigRequest, {"server": {"api": True}}),
        (m.PatchConfigRequest, {"server": {"api": []}}),
        (m.PatchConfigRequest, {"server": {"api": {"auth_header": "x"}}}),
        (m.PatchConfigRequest, {"server": {"api": {"auth_header": None}}}),
        (m.PatchConfigRequest, {"server": {"api": {"runtime_edge_enabled": None}}}),
        (m.ReloadRequest, {"mode": "drain"}),
        (m.ReloadRequest, {"mode": "instant", "timeout_secs": 10}),
        (m.ReloadRequest, {"mode": "drain", "timeout_secs": 3601}),
        (m.SessionQuery, {"limit": 201}),
        (m.SessionQuery, {"session_ref": SESSION, "limit": 1}),
        (m.SessionQuery, {"session_ref": SESSION, "cursor": SESSION}),
        (m.SessionQuery, {"ip": "2001:0db8::1"}),
        (m.SessionQuery, {"ip": "fe80::1%eth0"}),
        (m.SessionQuery, {"host": ""}),
        (m.SessionQuery, {"user": "я" * 33}),
        (m.SessionQuery, {"host": "x" * 254}),
        (m.SessionQuery, {"user_agent_id": "A" * 32}),
        (m.SessionQuery, {"key_id": "a" * 32}),
        (m.SessionQuery, {"state": "invalid"}),
        (m.FilterSelector, {}),
        (m.RefsSelector, {"session_refs": []}),
        (m.RefsSelector, {"session_refs": [SESSION, SESSION]}),
        (m.RuntimeInstanceRequest, {"runtime_instance": "A" * 32}),
        (
            m.CloseRequest,
            {"runtime_instance": "b" * 32, "selector": {"kind": "refs", "session_refs": [SESSION]}},
        ),
        (
            m.CloseRequest,
            {"runtime_instance": "b" * 32, "selector": {"kind": "filter", "session_ref": SESSION}},
        ),
        (
            m.CloseRequest,
            {"runtime_instance": INSTANCE, "selector": {"kind": "all", "unknown": True}},
        ),
    ],
)
def test_invalid_requests(model, values):
    with pytest.raises(ValidationError):
        model(**values)


def test_valid_requests_and_serialization():
    request = m.CreateUserRequest(username="alice", data_quota_bytes=100, quota_period="monthly")
    assert request.quota_period == "monthly"
    assert m.PatchUserRequest().model_dump(exclude_unset=True) == {}
    assert m.PatchUserRequest(enabled=None).model_dump(exclude_unset=True) == {"enabled": None}
    assert m.PatchUserRequest(secret="ab" * 16).secret == "ab" * 16
    assert "abab" not in repr(m.RotateSecretRequest(secret="ab" * 16))
    assert m.PatchUserRequest(expiration_rfc3339=None).expiration_rfc3339 is None
    assert m.PatchUserRequest(
        expiration_rfc3339="2026-12-01T00:00:00Z"
    ).expiration_rfc3339.endswith("Z")
    assert m.PatchConfigRequest(server={"listeners": []}).server == {"listeners": []}
    assert m.ReloadRequest().mode == "instant"
    assert m.SessionQuery(ip="2001:db8::1").ip == "2001:db8::1"
    assert m.SessionQuery(ip=None).ip is None
    assert m.SessionQuery(user=None).user is None
    assert (
        m.CloseRequest(runtime_instance=INSTANCE, selector=m.AllSelector()).selector.kind == "all"
    )
    assert (
        m.CloseRequest(
            runtime_instance=INSTANCE, selector=m.FilterSelector(session_ref=SESSION)
        ).selector.session_ref
        == SESSION
    )


def test_access_policy_patch_contract():
    patch = m.AccessPolicyPatch(
        user_max_tcp_conns_global_each=12,
        user_max_unique_ips_global_each=0,
        user_max_unique_ips_mode="combined",
        user_max_unique_ips_window_secs=120,
        cidr_rate_limits={
            "192.0.2.0/24": {"up_bps": 8_000_000, "down_bps": 16_000_000},
            "*4/24": {"down_bps": 4_000_000},
            "*6/64": {"up_bps": 2_000_000},
            "*/28": {"up_bps": 1_000_000},
            "2001:db8::/32": None,
            "203.0.113.129/24": None,
        },
    )
    assert patch.model_dump(exclude_unset=True) == {
        "user_max_tcp_conns_global_each": 12,
        "user_max_unique_ips_global_each": 0,
        "user_max_unique_ips_mode": "combined",
        "user_max_unique_ips_window_secs": 120,
        "cidr_rate_limits": {
            "192.0.2.0/24": {"up_bps": 8_000_000, "down_bps": 16_000_000},
            "*4/24": {"down_bps": 4_000_000},
            "*6/64": {"up_bps": 2_000_000},
            "*/28": {"up_bps": 1_000_000},
            "2001:db8::/32": None,
            "203.0.113.129/24": None,
        },
    }


def test_access_policy_patch_sparse_null_semantics():
    for mode in ("active_window", "time_window", "combined"):
        assert m.AccessPolicyPatch(user_max_unique_ips_mode=mode).user_max_unique_ips_mode == mode
    # A set scalar serializes; explicit null restores the server default.
    assert m.AccessPolicyPatch(user_max_tcp_conns_global_each=0).model_dump(exclude_unset=True) == {
        "user_max_tcp_conns_global_each": 0
    }
    assert m.AccessPolicyPatch(user_max_tcp_conns_global_each=None).model_dump(
        exclude_unset=True
    ) == {"user_max_tcp_conns_global_each": None}
    # A whole-map null clears every rule; a null entry deletes one rule.
    assert m.AccessPolicyPatch(cidr_rate_limits=None).model_dump(exclude_unset=True) == {
        "cidr_rate_limits": None
    }
    assert m.AccessPolicyPatch(cidr_rate_limits={"198.51.100.0/24": None}).model_dump(
        exclude_unset=True
    ) == {"cidr_rate_limits": {"198.51.100.0/24": None}}
    # The upper rate bound is accepted with a single positive direction; the
    # omitted direction stays absent and the server applies its zero default.
    assert m.AccessPolicyPatch(
        cidr_rate_limits={"192.0.2.0/24": {"up_bps": 100_000_000_000}}
    ).model_dump(exclude_unset=True) == {
        "cidr_rate_limits": {"192.0.2.0/24": {"up_bps": 100_000_000_000}}
    }
    # Non-canonical CIDR keys keep their authored spelling.
    assert m.AccessPolicyPatch(
        cidr_rate_limits={"192.0.2.129/24": {"up_bps": 1}}
    ).cidr_rate_limits == {"192.0.2.129/24": m.CidrRateLimitInput(up_bps=1)}


def test_user_source_deny_request_field():
    denied = ["203.0.113.0/24", "2001:db8:abcd::/48"]
    create = m.CreateUserRequest(username="alice", source_deny=denied)
    assert create.source_deny == denied
    assert m.CreateUserRequest(username="alice").model_dump(exclude_unset=True) == {
        "username": "alice"
    }
    assert m.CreateUserRequest(username="alice", source_deny=None).model_dump(
        exclude_unset=True
    ) == {"username": "alice", "source_deny": None}
    assert m.PatchUserRequest().model_dump(exclude_unset=True) == {}
    assert m.PatchUserRequest(source_deny=None).model_dump(exclude_unset=True) == {
        "source_deny": None
    }
    empty = m.PatchUserRequest(source_deny=[])
    assert empty.source_deny == []
    assert empty.model_dump(exclude_unset=True) == {"source_deny": []}
    # Host bits are allowed and preserved verbatim.
    assert m.CreateUserRequest(username="alice", source_deny=["192.0.2.129/24"]).source_deny == [
        "192.0.2.129/24"
    ]


def test_config_patch_network_and_server_api_allowlists():
    network = m.PatchConfigRequest(network={"dns_overrides": ["upstream.example:443:192.0.2.10"]})
    assert network.network == {"dns_overrides": ["upstream.example:443:192.0.2.10"]}
    assert m.PatchConfigRequest(network={"dns_overrides": []}).network == {"dns_overrides": []}
    api = {
        "minimal_runtime_enabled": True,
        "minimal_runtime_cache_ttl_ms": 0,
        "runtime_edge_enabled": True,
        "runtime_edge_cache_ttl_ms": 500,
        "runtime_edge_top_n": 20,
    }
    assert m.PatchConfigRequest(server={"api": api}).server == {"api": api}
    # A null observability member is retained when a concrete value accompanies it.
    mixed = m.PatchConfigRequest(server={"listeners": [], "api": {"runtime_edge_enabled": None}})
    assert mixed.model_dump(exclude_unset=True) == {
        "server": {"listeners": [], "api": {"runtime_edge_enabled": None}}
    }
    # Fully editable sections and the existing server.listeners guard stay intact.
    assert m.PatchConfigRequest(general={"fast_mode": True}).general == {"fast_mode": True}
    assert m.PatchConfigRequest(server={"listeners": []}).server == {"listeners": []}


def test_nullable_revision_envelope():
    payload = {"ok": True, "data": {"status": "ok", "read_only": False}}
    missing = m.NullableRevisionAPIResponse[m.HealthData].model_validate(
        {**payload, "revision": None}
    )
    assert missing.revision is None
    assert missing.data.status == "ok"
    assert missing.status_code == 200
    present = m.NullableRevisionAPIResponse[m.HealthData].model_validate(
        {**payload, "revision": "abc"}
    )
    assert present.revision == "abc"
    with pytest.raises(ValidationError):
        m.APIResponse[m.HealthData].model_validate({**payload, "revision": None})


def test_field_issue_dto():
    issue = m.FieldIssue(path="network.dns_overrides", code="invalid_entry", message="bad DNS")
    assert (issue.path, issue.code, issue.message) == (
        "network.dns_overrides",
        "invalid_entry",
        "bad DNS",
    )
    assert m.FieldIssue(path="p", code="c", message="m", future_upstream_field=1).model_extra == {
        "future_upstream_field": 1
    }
    with pytest.raises(ValidationError):
        m.FieldIssue(path="p", code="c")


def test_all_public_models_have_resolved_schema():
    for name in m.__all__:
        model = getattr(m, name)
        if isinstance(model, type) and issubclass(model, m.ResponseModel):
            assert model.model_json_schema()["title"] == name
