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


def _inherited_limit(*, value=None, configured_override=None, global_value=0, origin="unlimited"):
    return {
        "value": value,
        "configured_override": configured_override,
        "global_value": global_value,
        "origin": origin,
    }


def _limit_snapshot(max_tcp_conns=None, max_unique_ips=None):
    return {
        "max_tcp_conns": max_tcp_conns
        or _inherited_limit(value=4, configured_override=4, origin="user_override"),
        "max_unique_ips": max_unique_ips or _inherited_limit(),
    }


def _user_payload(**overrides):
    payload = {
        "username": "alice",
        "enabled": True,
        "in_runtime": True,
        "limits": {
            "desired": _limit_snapshot(),
            "effective": _limit_snapshot(),
            "effective_scope": "request_generation_snapshot",
            "subsystem_convergence": "unknown",
        },
        "source_deny": ["203.0.113.0/24", "2001:db8:abcd::/48"],
        "source_deny_status": {
            "effective": ["203.0.113.0/24", "2001:db8:abcd::/48"],
            "runtime_reload_required": False,
            "apply_mode": "generation_reload",
            "reload_endpoint": "POST /v1/system/reload",
            "effective_scope": "request_generation_snapshot",
        },
        "current_connections": 0,
        "active_unique_ips": 0,
        "active_unique_ips_list": [],
        "recent_unique_ips": 0,
        "recent_unique_ips_list": [],
        "total_octets": 0,
        "links": {"classic": [], "secure": [], "tls": [], "tls_domains": []},
    }
    payload.update(overrides)
    return payload


def test_user_info_exposes_limit_state_and_source_deny_status():
    user = m.UserInfo(**_user_payload())
    assert user.limits.desired.max_tcp_conns.origin == "user_override"
    assert user.limits.desired.max_tcp_conns.value == 4
    assert user.limits.desired.max_unique_ips.origin == "unlimited"
    assert user.limits.effective is not None
    assert user.limits.effective.max_unique_ips.value is None
    assert user.limits.effective_scope == "request_generation_snapshot"
    assert user.limits.subsystem_convergence == "unknown"
    assert user.source_deny == ["203.0.113.0/24", "2001:db8:abcd::/48"]
    status = user.source_deny_status
    assert status.effective == ["203.0.113.0/24", "2001:db8:abcd::/48"]
    assert status.runtime_reload_required is False
    assert status.apply_mode == "generation_reload"
    assert status.reload_endpoint == "POST /v1/system/reload"
    assert status.effective_scope == "request_generation_snapshot"


def test_user_limit_state_and_source_deny_state_nullability():
    # The desired snapshot is always present; the effective one is nullable.
    state = m.UserLimitState(
        desired=_limit_snapshot(),
        effective_scope="active_config_snapshot",
        subsystem_convergence="unknown",
    )
    assert state.effective is None
    with pytest.raises(ValidationError):
        m.UserLimitState()
    # Rust always serializes null for unset optionals on these DTOs.
    limit = m.InheritedLimit(global_value=8, origin="global_default")
    assert limit.value is None
    assert limit.configured_override is None
    with pytest.raises(ValidationError):
        m.InheritedLimit()
    deny = m.SourceDenyState(
        apply_mode="generation_reload",
        reload_endpoint="POST /v1/system/reload",
        effective_scope="request_generation_snapshot",
    )
    assert deny.effective is None
    assert deny.runtime_reload_required is None
    with pytest.raises(ValidationError):
        m.SourceDenyState()


def test_patch_config_response_exposes_changed_paths_and_normalization_effects():
    response = m.PatchConfigResponse(
        revision="a" * 64,
        restart_required=True,
        runtime_reload_required=True,
        process_restart_required=False,
        deferred_process_fields=[],
        changed=["censorship"],
        changed_paths=["censorship.tls_domain"],
        normalization_effects=[
            {"path": "upstreams[0].bindtodevice", "code": "alias_canonicalized"}
        ],
    )
    assert response.changed_paths == ["censorship.tls_domain"]
    effect = response.normalization_effects[0]
    assert effect.path == "upstreams[0].bindtodevice"
    assert effect.code == "alias_canonicalized"
    assert response.reload is None
    with pytest.raises(ValidationError):
        m.PatchConfigResponse(
            revision="a" * 64,
            restart_required=False,
            runtime_reload_required=False,
            process_restart_required=False,
            deferred_process_fields=[],
            changed=["censorship"],
        )


def test_config_data_includes_network_dns_overrides():
    data = m.ConfigData(
        general={},
        timeouts={},
        censorship={},
        upstreams=[],
        dc_overrides={},
        web={},
        network={"dns_overrides": ["upstream.example:443:192.0.2.10"]},
    )
    assert data.network == {"dns_overrides": ["upstream.example:443:192.0.2.10"]}
    without = m.ConfigData(
        general={}, timeouts={}, censorship={}, upstreams=[], dc_overrides={}, web={}
    )
    assert without.network is None


def test_all_public_models_have_resolved_schema():
    for name in m.__all__:
        model = getattr(m, name)
        if isinstance(model, type) and issubclass(model, m.ResponseModel):
            assert model.model_json_schema()["title"] == name


CAPABILITIES_DATA = {
    "api_version": "v1",
    "schema_version": 1,
    "software_version": "3.5.17",
    "config_schema": "/v1/config/schema",
    "read_only": False,
    "availability_scope": "feature_and_runtime_source_prerequisites_not_request_success",
    "operations": [
        {
            "id": "health",
            "method": "GET",
            "path": "/v1/health",
            "gate": "always",
            "success": [200],
            "supported": True,
            "enabled": True,
            "available": True,
            "mutable": False,
        },
        {
            "id": "config_validate",
            "method": "POST",
            "path": "/v1/config/validate",
            "gate": "always",
            "success": [200],
            "body": "PatchConfigRequest",
            "if_match": True,
            "if_runtime_match": True,
            "read_only_operation": True,
            "supported": True,
            "enabled": True,
            "available": None,
            "mutable": False,
            "unavailable_reason": "availability_not_sampled",
        },
        {
            "id": "users_create",
            "method": "POST",
            "path": "/v1/users",
            "aliases": ["/v1/users/"],
            "gate": "always",
            "success": [200, 409],
            "credential_bearing": True,
            "optional_body": True,
            "exact_json_content_type": True,
            "supported": True,
            "enabled": False,
            "available": False,
            "mutable": True,
            "disabled_reason": "api_disabled",
            "mutation_blocked_reason": "read_only",
        },
    ],
}


def test_capabilities_data_parses_without_openapi_artifact():
    # API.md lists openapi_artifact, but the 3.5.17 Rust DTO never serializes it;
    # the payload above deliberately omits it and must parse unchanged.
    data = m.CapabilitiesData(**CAPABILITIES_DATA)
    assert data.api_version == "v1"
    assert data.schema_version == 1
    assert data.software_version == "3.5.17"
    assert data.config_schema == "/v1/config/schema"
    assert data.read_only is False
    assert data.operations[0].aliases == []
    assert data.operations[0].body is None
    assert data.operations[0].disabled_reason is None
    assert data.operations[0].unavailable_reason is None
    assert data.operations[0].mutation_blocked_reason is None
    validate = data.operations[1]
    assert validate.body == "PatchConfigRequest"
    assert validate.if_match is True
    assert validate.if_runtime_match is True
    assert validate.read_only_operation is True
    assert validate.available is None
    assert validate.unavailable_reason == "availability_not_sampled"
    create = data.operations[2]
    assert create.aliases == ["/v1/users/"]
    assert create.credential_bearing is True
    assert create.optional_body is True
    assert create.exact_json_content_type is True
    assert create.disabled_reason == "api_disabled"
    assert create.mutation_blocked_reason == "read_only"
    envelope = m.APIResponse[m.CapabilitiesData].model_validate(
        {"ok": True, "revision": "abc", "data": CAPABILITIES_DATA}
    )
    assert envelope.data.operations[1].available is None
    assert envelope.revision == "abc"


def test_operation_capability_defaults_and_strictness():
    operation = m.OperationCapability(
        id="health",
        method="GET",
        path="/v1/health",
        gate="always",
        success=[200],
        supported=True,
        enabled=True,
        mutable=False,
    )
    # Rust serde defaults: skipped arrays and reasons parse as empty/absent,
    # gate and precondition flags default to false.
    assert operation.aliases == []
    assert operation.credential_bearing is False
    assert operation.body is None
    assert operation.optional_body is False
    assert operation.exact_json_content_type is False
    assert operation.if_match is False
    assert operation.if_runtime_match is False
    assert operation.read_only_operation is False
    assert operation.available is None
    assert operation.disabled_reason is None
    assert operation.unavailable_reason is None
    assert operation.mutation_blocked_reason is None
    with pytest.raises(ValidationError):
        m.OperationCapability(id="health", method="GET", path="/v1/health", success=[200])
    with pytest.raises(ValidationError):
        m.OperationCapability(
            id="health", method="GET", path="/v1/health", gate="always", success=["200"]
        )
    with pytest.raises(ValidationError):
        m.OperationCapability(
            id="health",
            method="GET",
            path="/v1/health",
            gate="always",
            success=[200],
            supported=True,
            enabled=True,
            aliases=["/v1/health/"],
        )
    # A future upstream flag is preserved rather than rejected.
    future = m.OperationCapability(
        id="health",
        method="GET",
        path="/v1/health",
        gate="always",
        success=[200],
        supported=True,
        enabled=True,
        mutable=False,
        future_upstream_flag=True,
    )
    assert future.model_extra == {"future_upstream_flag": True}


def _apply_policy(**overrides):
    policy = {
        "watcher": "supported",
        "reload": "supported",
        "effect": "admission_or_accounting_policy_consumption_no_implicit_quota_reset",
    }
    policy.update(overrides)
    return policy


def _field_api(**overrides):
    api = {
        "config_read": False,
        "config_write": False,
        "read_routes": [],
        "write_routes": [],
        "null_behavior": "not_editable",
    }
    api.update(overrides)
    return api


def test_config_schema_data_parses_field_metadata():
    data = m.ConfigSchemaData(
        schema_version=1,
        value_schema_dialect="https://json-schema.org/draft/2020-12/schema",
        defaults_scope="unconfigured_type_defaults_before_loader_normalization",
        validation_scope="value_constraints_are_not_a_substitute_for_full_config_validation",
        path_notation="dot_members; []=array_element; {name}=dynamic_map_key",
        config_patch={
            "objects": "recursive_merge",
            "arrays": "replace_whole_array",
            "object_null_members": "ignored_before_candidate_validation",
            "reset": "not_supported",
            "source_ownership": "one_independently_writable_source_per_mutation",
            "if_match": "optional_source_manifest_revision",
        },
        fields=[
            {
                "path": "access.cidr_rate_limits.{cidr}.down_bps",
                "value": {"type": "integer", "minimum": 0, "maximum": 100000000000},
                "default_kind": "map_entry",
                "sensitivity": "public",
                "description": "Download limit in bits-per-second.",
                "unit": "bits_per_second",
                "apply": _apply_policy(),
                "constraints": ["At least one direction must be nonzero; zero means unlimited."],
                "api": _field_api(
                    read_routes=["GET /v1/access/policy"],
                    write_routes=["PATCH /v1/access/policy"],
                    request_field="cidr_rate_limits",
                    non_editable_reason="managed_via_access_policy_api",
                    null_behavior="clear_map_or_remove_null_entries",
                ),
            },
            {
                "path": "general.me_adaptive_floor_cpu_cores_override",
                "value": {"type": "integer", "minimum": 0, "maximum": 65535},
                "default_kind": "type_default",
                "sensitivity": "public",
                "description": "Override logical CPU core count.",
                "default": 0,
                "apply": _apply_policy(effect="next_subsystem_policy_consumption_or_me_update"),
                "dependencies": ["general.use_middle_proxy"],
                "api": _field_api(
                    config_read=True,
                    config_write=True,
                    read_routes=["GET /v1/config"],
                    write_routes=["PATCH /v1/config"],
                    null_behavior="ignored_member_then_validate_candidate",
                ),
            },
            {
                "path": "network.dns_overrides",
                "value": {"type": "array", "items": {"type": "string"}, "maxItems": 4096},
                "default_kind": "type_default",
                "sensitivity": "public",
                "description": "Runtime DNS overrides in `host:port:ip` format.",
                "default": [],
                "apply": _apply_policy(effect="future_resolutions_existing_connections_unchanged"),
                "api": _field_api(
                    config_read=True,
                    config_write=True,
                    read_routes=["GET /v1/config"],
                    write_routes=["PATCH /v1/config"],
                    null_behavior="ignored_member_then_validate_candidate",
                ),
            },
        ],
    )
    assert data.config_patch.reset == "not_supported"
    assert data.config_patch.if_match == "optional_source_manifest_revision"
    cidr = data.fields[0]
    assert cidr.value == {"type": "integer", "minimum": 0, "maximum": 100000000000}
    assert cidr.default is None
    assert "default" not in cidr.model_fields_set
    assert cidr.unit == "bits_per_second"
    assert cidr.aliases == []
    assert cidr.dependencies == []
    assert cidr.constraints == ["At least one direction must be nonzero; zero means unlimited."]
    assert cidr.api.request_field == "cidr_rate_limits"
    assert cidr.api.non_editable_reason == "managed_via_access_policy_api"
    cores = data.fields[1]
    assert cores.default == 0
    assert cores.dependencies == ["general.use_middle_proxy"]
    assert cores.api.config_write is True
    dns = data.fields[2]
    # Arbitrary JSON defaults round-trip untouched, including an empty array.
    assert dns.default == []
    envelope = m.APIResponse[m.ConfigSchemaData].model_validate(
        {"ok": True, "revision": "abc", "data": data.model_dump()}
    )
    assert envelope.data.fields[1].default == 0


def test_field_metadata_default_presence_versus_null_default():
    # `default_kind="unset"` serializes an explicit null default; other kinds
    # omit the member entirely, which Pydantic field-set data must distinguish.
    unset = m.FieldMetadata(
        path="censorship.mask_host",
        value={"type": "string"},
        default_kind="unset",
        sensitivity="public",
        description="Mask host.",
        apply=_apply_policy(watcher="unsupported"),
        api=_field_api(),
        default=None,
    )
    assert "default" in unset.model_fields_set
    assert unset.default is None
    redacted = m.FieldMetadata(
        path="access.users",
        value={"type": "object", "additionalProperties": {"type": "string"}},
        default_kind="redacted",
        sensitivity="credential",
        description="User secrets.",
        apply=_apply_policy(),
        api=_field_api(null_behavior="unchanged_on_user_patch"),
    )
    assert "default" not in redacted.model_fields_set
    assert redacted.default is None
    with pytest.raises(ValidationError):
        m.FieldMetadata(
            path="access.users",
            value={"type": "object"},
            default_kind="redacted",
            sensitivity="credential",
            description="User secrets.",
            api=_field_api(),
        )


def test_discovery_models_require_core_fields():
    without_version = {
        key: value for key, value in CAPABILITIES_DATA.items() if key != "software_version"
    }
    with pytest.raises(ValidationError):
        m.CapabilitiesData(**without_version)
    with pytest.raises(ValidationError):
        m.ConfigSchemaData(
            schema_version=1,
            value_schema_dialect="https://json-schema.org/draft/2020-12/schema",
            defaults_scope="s",
            validation_scope="s",
            path_notation="s",
            config_patch={
                "objects": "recursive_merge",
                "arrays": "replace_whole_array",
                "object_null_members": "ignored",
                "source_ownership": "one",
                "if_match": "optional",
            },
            fields=[],
        )
    with pytest.raises(ValidationError):
        m.ConfigPatchSemantics(
            objects="recursive_merge",
            arrays="replace_whole_array",
            object_null_members="ignored",
            source_ownership="one",
            if_match="optional",
        )
    with pytest.raises(ValidationError):
        m.FieldApi(
            config_read=True,
            config_write=True,
            read_routes=[],
            write_routes=[],
        )
    with pytest.raises(ValidationError):
        m.ApplyPolicy(watcher="supported", reload="supported")
