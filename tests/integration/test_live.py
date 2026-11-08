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

from telemt import ClientHook, ConflictError, TelemtClient
from telemt import models as m

from ..test_resources import READ_ROUTES, WRITE_ROUTES, resolve

pytestmark = pytest.mark.skipif(
    not os.environ.get("TELEMT_TEST_URL") or not os.environ.get("TELEMT_TEST_WEB_URL"),
    reason="requires a disposable Telemt instance (see docs/testing.md)",
)


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

            users = await call("users.list")
            assert [user.username for user in users.data] == ["audit_admin"], (
                "Use only the disposable tests/integration/telemt.toml instance"
            )
            for name, _, args in READ_ROUTES:
                if not args:
                    await call(name)

            created = await call(
                "users.create",
                m.CreateUserRequest(
                    username="sdk_test",
                    max_tcp_conns=4,
                    data_quota_bytes=1000000,
                    quota_period="monthly",
                ),
            )
            assert created.data.user.username == "sdk_test"
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

            config = await call("config.get")
            await call(
                "config.update",
                m.PatchConfigRequest(general={"log_level": "silent"}),
                revision=config.revision,
            )
            reload = await call("system.reload", m.ReloadRequest())
            async with asyncio.timeout(20):
                while True:
                    result = await call("system.reload_status", reload.data.reload_id)
                    if result.data.state in {"succeeded", "failed", "rolled_back"}:
                        break
                    await asyncio.sleep(0.1)
            result = await client.system.wait_reload(reload.data.reload_id, timeout=20)
            assert result.data.state == "succeeded", result.data

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
