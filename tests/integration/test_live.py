"""Opt-in mutation tests for a disposable Telemt instance; see docs/testing.md."""

import asyncio
import base64
import hmac
import json
import os
import re
from pathlib import Path

import httpx
import pytest

from telemt import APIError, ClientHook, ConflictError, TelemtClient
from telemt import models as m

from ..test_resources import READ_ROUTES, WRITE_ROUTES, resolve

pytestmark = pytest.mark.skipif(
    not os.environ.get("TELEMT_TEST_URL") or not os.environ.get("TELEMT_TEST_WEB_URL"),
    reason="requires a disposable Telemt instance (see docs/testing.md)",
)

_STATE_SECTIONS = {
    "general",
    "network",
    "server",
    "timeouts",
    "censorship",
    "upstreams",
    "dc_overrides",
    "web",
    "access",
    "logging",
    "root",
}


async def test_all_operations_against_telemt():
    records = []
    current_method = ""

    async def record(response):
        await response.aread()
        records.append(
            {
                "method": current_method,
                "status_code": response.status_code,
                "body": response.json(),
            }
        )

    hook_requests = []
    hook_responses = []

    class AuditHook(ClientHook):
        async def on_request(self, request):
            hook_requests.append(request)

        async def on_response(self, response):
            assert response.content
            hook_responses.append(response)

    async with httpx.AsyncClient(event_hooks={"response": [record]}) as http:
        async with TelemtClient(
            os.environ["TELEMT_TEST_URL"],
            auth_header="sdk-audit-test-auth",
            http_client=http,
            hooks=[AuditHook()],
        ) as client:

            async def call(name, *args, **kwargs):
                nonlocal current_method
                current_method = name
                return await resolve(client, name)(*args, **kwargs)

            async def wait_published():
                """Wait until the watcher consumes every pending config write.

                Fenced config writes race the watcher's asynchronous publication:
                sampling preconditions before it settles makes the next write flap
                with 409 runtime_conflict, so wait for a fully published snapshot.
                """
                async with asyncio.timeout(15):
                    while True:
                        published = await call("config.state")
                        data = published.data
                        if (
                            data.desired_status == "valid"
                            and data.watcher_matches_desired is True
                            and data.comparison.status == "published_match"
                        ):
                            return
                        await asyncio.sleep(0.1)

            async def wait_reload(reload_id):
                nonlocal current_method
                current_method = "system.reload_status"
                return await client.system.wait_reload(reload_id, timeout=20)

            users = await call("users.list")
            assert [user.username for user in users.data] == ["audit_admin"], (
                "Use only the disposable tests/integration/telemt.toml instance"
            )
            for name, _, args in READ_ROUTES:
                if not args:
                    await call(name)

            capabilities = await call("discovery.capabilities")
            assert capabilities.data.api_version == "v1"
            assert capabilities.data.schema_version == 1
            assert capabilities.data.software_version == "3.5.17"
            by_id = {op.id: op for op in capabilities.data.operations}
            assert by_id["config_state"].path == "/v1/config/state"
            validate_op = by_id["config_validate"]
            assert validate_op.body == "PatchConfigRequest"
            assert validate_op.read_only_operation is True
            assert validate_op.if_match and validate_op.if_runtime_match
            policy_op = by_id["access_policy_patch"]
            assert policy_op.mutable and policy_op.if_match and policy_op.if_runtime_match
            assert by_id["access_policy_get"].path == "/v1/access/policy"

            schema = await call("config.schema")
            assert schema.data.schema_version == 1
            assert schema.data.config_patch.objects == "recursive_merge"
            assert schema.data.config_patch.reset == "not_supported"
            schema_fields = {field.path: field for field in schema.data.fields}
            assert schema_fields["network.dns_overrides"].api.config_write is True
            assert "server.api.runtime_edge_top_n" in schema_fields

            filtered_state = await call("config.state", ["network"])
            assert filtered_state.data.sections == ["network"]
            assert filtered_state.revision is not None
            assert filtered_state.data.desired_status == "valid"
            state = await call("config.state")
            assert set(state.data.sections) == _STATE_SECTIONS
            assert state.revision == state.data.desired_revision
            assert state.data.scope == "published_configuration_not_subsystem_acknowledgment"
            assert state.data.subsystem_convergence == "unknown"
            assert state.data.comparison.scope == "selected_sections"
            assert state.data.runtime.runtime_match

            created = await call(
                "users.create",
                m.CreateUserRequest(
                    username="sdk_test",
                    max_tcp_conns=4,
                    data_quota_bytes=1000000,
                    quota_period="monthly",
                    source_deny=["203.0.113.0/24"],
                ),
            )
            assert created.data.user.username == "sdk_test"
            assert created.data.user.source_deny == ["203.0.113.0/24"]
            assert created.data.user.source_deny_status.runtime_reload_required is True
            original_secret = created.data.secret
            assert len(original_secret) == 32
            user = await call("users.get", "sdk_test")
            changed = await call(
                "users.update",
                "sdk_test",
                m.PatchUserRequest(max_tcp_conns=None, secret=None),
                revision=user.revision,
            )
            assert changed.data.max_tcp_conns is None
            with pytest.raises(ConflictError):
                await call(
                    "users.update",
                    "sdk_test",
                    m.PatchUserRequest(enabled=False),
                    revision="stale-revision",
                )
            assert not (await call("users.disable", "sdk_test")).data.enabled
            assert (await call("users.enable", "sdk_test")).data.enabled
            rotated = await call("users.rotate_secret", "sdk_test")
            assert rotated.data.secret != original_secret
            assert (await call("users.reset_quota", "sdk_test")).data.used_bytes == 0
            assert any(u.username == "sdk_test" for u in (await call("stats.quota")).data.users)

            deny_view = await call("users.get", "sdk_test")
            replaced = await call(
                "users.update",
                "sdk_test",
                m.PatchUserRequest(source_deny=["198.51.100.0/24", "2001:db8:abcd::/48"]),
                revision=deny_view.revision,
            )
            assert replaced.data.source_deny == ["198.51.100.0/24", "2001:db8:abcd::/48"]
            assert replaced.data.source_deny_status.runtime_reload_required is True
            deny_reload = await call("system.reload", m.ReloadRequest())
            deny_result = await wait_reload(deny_reload.data.reload_id)
            assert deny_result.data.state == "succeeded"
            denied = await call("users.get", "sdk_test")
            assert denied.data.source_deny_status.effective == [
                "198.51.100.0/24",
                "2001:db8:abcd::/48",
            ]
            assert denied.data.source_deny_status.runtime_reload_required is False
            cleared_deny = await call(
                "users.update",
                "sdk_test",
                m.PatchUserRequest(source_deny=None),
                revision=denied.revision,
            )
            assert cleared_deny.data.source_deny == []
            assert cleared_deny.data.source_deny_status.runtime_reload_required is True
            clear_reload = await call("system.reload", m.ReloadRequest())
            clear_result = await wait_reload(clear_reload.data.reload_id)
            assert clear_result.data.state == "succeeded"
            cleared_view = await call("users.get", "sdk_test")
            assert cleared_view.data.source_deny_status.effective == []
            assert cleared_view.data.source_deny_status.runtime_reload_required is False
            await call("users.delete", "sdk_test")

            key = bytes.fromhex("dd0123456789abcdef0123456789abcdef")
            capability = (
                base64.urlsafe_b64encode(
                    hmac.digest(key, b"tdesktop-web-proxy-bridge-v1\nproxy.example.com", "sha256")
                )
                .rstrip(b"=")
                .decode()
            )
            async with httpx.AsyncClient(
                base_url=os.environ["TELEMT_TEST_WEB_URL"],
                headers={
                    "Host": "proxy.example.com",
                    "X-Forwarded-For": "192.0.2.19",
                    "User-Agent": "Telemt-SDK-Test/1",
                },
            ) as ingress:
                bridge = await ingress.get("/", params={"bridge": capability})
                assert bridge.status_code == 200
                bootstrap = re.search(r'bootstrap="([^"]+)"', bridge.text)
                assert bootstrap is not None
                session = await ingress.post(
                    "/api/v1/session",
                    headers={
                        "Authorization": "Bearer " + bootstrap[1],
                        "Content-Type": "application/octet-stream",
                    },
                    content=bytes.fromhex("100000000000000101"),
                )
                assert session.status_code == 200

            status = (await call("runtime.web.status")).data
            assert status.runtime is not None
            instance = status.runtime.runtime_instance
            page = (await call("runtime.web.sessions", m.SessionQuery(user="audit_admin"))).data
            assert page.sessions
            rows = [
                row
                async for row in client.runtime.web.iter_sessions(
                    m.SessionQuery(user="audit_admin", limit=1)
                )
            ]
            assert ref_set(rows) == ref_set(page.sessions)
            ref = page.sessions[-1].session_ref
            assert isinstance((await call("runtime.web.session", ref)).data, m.SessionRow)
            operation = await call(
                "runtime.web.close_sessions",
                m.CloseRequest(
                    runtime_instance=instance, selector=m.RefsSelector(session_refs=[ref])
                ),
            )
            async with asyncio.timeout(10):
                while True:
                    progress = await call("runtime.web.operation", operation.data.operation_id)
                    if progress.data.state in {"completed", "failed"}:
                        break
                    await asyncio.sleep(0.05)
            progress = await client.runtime.web.wait_operation(
                operation.data.operation_id, timeout=10
            )
            assert progress.data.state == "completed"
            assert progress.data.close_signalled == 1
            async with asyncio.timeout(10):
                while True:
                    gone = await call("runtime.web.session", ref)
                    if gone.status_code == 410:
                        break
                    await asyncio.sleep(0.05)
            assert isinstance(gone.data, m.GoneSessionData)

            request = m.RuntimeInstanceRequest(runtime_instance=instance)
            await call("runtime.web.clear_debug", request)
            await call("runtime.web.reset_carrier_learning", request)
            paused = await call("runtime.web.pause", request)
            assert paused.data.state == "paused"
            assert paused.data.effective_new_work_admission is False
            await call(
                "runtime.web.drain", m.DrainRequest(runtime_instance=instance, timeout_secs=1)
            )
            resumed = await call("runtime.web.resume", request)
            assert resumed.data.state == "running"
            assert resumed.data.effective_new_work_admission is True

            preflight = await call(
                "config.validate",
                m.PatchConfigRequest(
                    network={"dns_overrides": ["upstream.example:443:192.0.2.10"]}
                ),
            )
            assert preflight.data.valid is True
            assert preflight.revision == preflight.data.base_revision
            assert "network" in preflight.data.touched_sections
            assert any(
                path.startswith("network.dns_overrides") for path in preflight.data.changed_paths
            )
            with pytest.raises(APIError) as invalid:
                await call(
                    "config.validate",
                    m.PatchConfigRequest(general={"unknown_telemetry_flag": True}),
                )
            assert invalid.value.status_code == 400
            assert invalid.value.code == "bad_request"
            assert any(
                detail.code == "unknown_field" and "unknown_telemetry_flag" in detail.path
                for detail in invalid.value.details
            )

            patched = await call(
                "config.update",
                m.PatchConfigRequest(
                    network={"dns_overrides": ["upstream.example:443:192.0.2.10"]}
                ),
                revision=preflight.revision,
                runtime_match=preflight.data.runtime.runtime_match,
            )
            assert any(
                path.startswith("network.dns_overrides") for path in patched.data.changed_paths
            )
            assert (await call("config.get")).data.network["dns_overrides"] == [
                "upstream.example:443:192.0.2.10"
            ]
            await wait_published()
            with pytest.raises(ConflictError) as stale_source:
                await call(
                    "config.update",
                    m.PatchConfigRequest(network={"dns_overrides": []}),
                    revision="stale-revision",
                )
            assert stale_source.value.code == "revision_conflict"

            current = await call("config.get")
            observability = await call(
                "config.update",
                m.PatchConfigRequest(server={"api": {"runtime_edge_top_n": 20}}),
                revision=current.revision,
            )
            assert "server.api.runtime_edge_top_n" in observability.data.changed_paths
            assert observability.data.runtime_reload_required is True
            assert observability.data.restart_required is True
            reload = await call("system.reload", m.ReloadRequest())
            async with asyncio.timeout(20):
                while True:
                    result = await call("system.reload_status", reload.data.reload_id)
                    if result.data.state in {"succeeded", "failed", "rolled_back"}:
                        break
                    await asyncio.sleep(0.1)
            result = await wait_reload(reload.data.reload_id)
            assert result.data.state == "succeeded", result.data

            with pytest.raises(ConflictError) as stale_runtime:
                await call(
                    "config.update",
                    m.PatchConfigRequest(network={"dns_overrides": []}),
                    runtime_match=preflight.data.runtime.runtime_match,
                )
            assert stale_runtime.value.code == "runtime_conflict"

            fresh_state = await call("config.state", ["network"])
            fresh_config = await call("config.get")
            cleared = await call(
                "config.update",
                m.PatchConfigRequest(network={"dns_overrides": []}),
                revision=fresh_config.revision,
                runtime_match=fresh_state.data.runtime.runtime_match,
            )
            assert any(
                path.startswith("network.dns_overrides") for path in cleared.data.changed_paths
            )
            assert (await call("config.get")).data.network["dns_overrides"] == []
            await wait_published()

            policy = await call("access.get")
            original = policy.data.desired
            updated = await call(
                "access.update",
                m.AccessPolicyPatch(
                    user_max_tcp_conns_global_each=8,
                    cidr_rate_limits={
                        "198.51.100.0/24": m.CidrRateLimitInput(
                            up_bps=1_000_000, down_bps=2_000_000
                        )
                    },
                ),
                revision=policy.revision,
                runtime_match=policy.data.runtime.runtime_match,
            )
            assert updated.data.desired.user_max_tcp_conns_global_each == 8
            rule = updated.data.desired.cidr_rate_limits["198.51.100.0/24"]
            assert (rule.up_bps, rule.down_bps) == (1_000_000, 2_000_000)
            assert "access.user_max_tcp_conns_global_each" in (updated.data.changed_paths or [])
            await wait_published()
            fresh_policy = await call("access.get")
            restored = await call(
                "access.update",
                m.AccessPolicyPatch(
                    user_max_tcp_conns_global_each=None,
                    cidr_rate_limits={"198.51.100.0/24": None},
                ),
                revision=fresh_policy.revision,
                runtime_match=fresh_policy.data.runtime.runtime_match,
            )
            assert restored.data.desired.user_max_tcp_conns_global_each == (
                original.user_max_tcp_conns_global_each
            )
            assert "198.51.100.0/24" not in restored.data.desired.cidr_rate_limits
            assert restored.data.desired.cidr_rate_limits == original.cidr_rate_limits

    assert len(hook_requests) == len(hook_responses)
    assert any(response.status_code == 409 for response in hook_responses)
    successful = [r for r in records if r["body"]["ok"]]
    expected = {r[0] for r in READ_ROUTES + WRITE_ROUTES}
    assert {r["method"] for r in successful} == expected
    if output := os.environ.get("TELEMT_TEST_RECORD"):
        # Keep distinct states (e.g. live/gone sessions) and one copy of repeated polls.
        unique = {
            (
                r["method"],
                r["status_code"],
                r["body"]["data"].get("state") if isinstance(r["body"]["data"], dict) else None,
            ): r
            for r in successful
        }
        await asyncio.to_thread(
            Path(output).write_text,
            json.dumps(list(unique.values()), indent=2) + "\n",
            encoding="utf-8",
        )


def ref_set(rows):
    return {row.session_ref for row in rows}
