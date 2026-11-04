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
        (m.PatchConfigRequest, {}),
        (m.PatchConfigRequest, {"general": None}),
        (m.PatchConfigRequest, {"access": {}}),
        (m.PatchConfigRequest, {"server": {"api": {}}}),
        (m.PatchConfigRequest, {"server": {}}),
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


def test_all_public_models_have_resolved_schema():
    for name in m.__all__:
        model = getattr(m, name)
        if isinstance(model, type) and issubclass(model, m.ResponseModel):
            assert model.model_json_schema()["title"] == name
