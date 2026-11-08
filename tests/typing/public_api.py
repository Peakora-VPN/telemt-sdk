"""Compile-only consumer examples: mypy must retain concrete types through every layer."""

from typing import assert_type

import httpx

from telemt import ClientHook, TelemtClient
from telemt import models as m


async def consumer(client: TelemtClient) -> None:
    assert_type(await client.health.get(), m.APIResponse[m.HealthData])
    assert_type((await client.users.list()).data, list[m.UserInfo])
    assert_type((await client.users.get("alice")).data.links.tls_domains, list[m.TlsDomainLink])
    assert_type((await client.users.create(m.CreateUserRequest(username="alice"))).data.secret, str)
    assert_type(
        await client.runtime.web.session("reference"),
        m.APIResponse[m.GoneSessionData | m.SessionRow],
    )
    status = (await client.runtime.web.status()).data
    assert_type(status.ingress, m.WebIngressStatus)
    assert_type(status.runtime, m.WebRuntimeStatus | None)
    if status.runtime is not None:
        assert_type(status.runtime.manager, m.WebManagerStatus | None)
        assert_type(status.runtime.permits, list[tuple[str, m.WebPermitStatus]])
        if status.runtime.manager is not None:
            assert_type(status.runtime.manager.issuance_enabled, bool)
    page = (await client.runtime.web.sessions()).data
    assert_type(page.scanned, int)
    assert_type(page.sessions, list[m.SessionRow])
    for session in page.sessions:
        assert_type(session.client_ip, str)
        assert_type(session.streams, int)
    selftest = (await client.runtime.me_selftest()).data.data
    if selftest is not None:
        assert_type(selftest.upstreams, list[m.RuntimeMeSelftestUpstreamData] | None)
        assert_type(selftest.bnd, m.RuntimeMeSelftestBndData | None)
    assert_type(
        await client.config.update(m.PatchConfigRequest(web={"enabled": False})),
        m.APIResponse[m.PatchConfigResponse],
    )
    # These ignores must remain necessary: accepting these calls would lose public type safety.
    await client.users.get(123)  # type: ignore[arg-type]
    await client.users.create(m.PatchUserRequest())  # type: ignore[arg-type]
    m.CreateUserRequest(username="alice", enabled="false")  # type: ignore[arg-type]


class ConsumerHook(ClientHook):
    async def on_request(self, request: httpx.Request) -> None:
        assert_type(request, httpx.Request)

    async def on_response(self, response: httpx.Response) -> None:
        assert_type(response, httpx.Response)


def hooked_client() -> TelemtClient:
    return TelemtClient("http://localhost", hooks=[ConsumerHook()])
