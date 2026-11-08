import asyncio

import httpx
import pytest

from telemt import ClientHook, InvalidResponseError, TelemtClient


async def test_hook_order_and_shared_http_client(user_data):
    events = []

    class Hook(ClientHook):
        def __init__(self, name):
            self.name = name

        async def on_request(self, request):
            events.append((self.name, "request"))
            request.headers["X-Hook"] = self.name

        async def on_response(self, response):
            assert response.content
            events.append((self.name, "response"))

    async def native(request):
        events.append(("httpx", "request"))

    def handle(request):
        assert request.headers["X-Hook"] == "second"
        return httpx.Response(200, json={"ok": True, "data": [user_data], "revision": "a" * 64})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), event_hooks={"request": [native]}
    ) as http:
        hooks = [Hook("first"), Hook("second")]
        async with TelemtClient("http://localhost", http_client=http, hooks=hooks) as client:
            hooks.clear()
            await client.users.list()
        assert not http.is_closed
        assert len(http.event_hooks["request"]) == 1
    assert events == [
        ("first", "request"),
        ("second", "request"),
        ("httpx", "request"),
        ("first", "response"),
        ("second", "response"),
    ]


async def test_response_hook_before_invalid_response():
    seen = []

    class Hook(ClientHook):
        async def on_response(self, response):
            seen.append(response.status_code)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(500, text="bad gateway"))
    ) as http:
        async with TelemtClient("http://localhost", http_client=http, hooks=[Hook()]) as client:
            with pytest.raises(InvalidResponseError):
                await client.health.get()
    assert seen == [500]


@pytest.mark.parametrize("phase", ["request", "response"])
async def test_callback_error_propagates(phase):
    error = httpx.ReadTimeout("hook failure")

    class Hook(ClientHook):
        async def on_request(self, request):
            if phase == "request":
                raise error

        async def on_response(self, response):
            raise error

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={}))
    ) as http:
        async with TelemtClient("http://localhost", http_client=http, hooks=[Hook()]) as client:
            with pytest.raises(httpx.ReadTimeout) as caught:
                await client.health.get()
            assert caught.value is error


async def test_concurrent_requests_keep_extension_state(user_data):
    seen = []

    class Hook(ClientHook):
        async def on_request(self, request):
            request.extensions["hook_path"] = request.url.path

        async def on_response(self, response):
            assert response.request.extensions["hook_path"] == response.request.url.path
            seen.append(response.request.url.path)

    async def handler(request):
        await asyncio.sleep(0)
        data = [user_data] if request.url.path.endswith("/users") else user_data
        return httpx.Response(200, json={"ok": True, "data": data, "revision": "a" * 64})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with TelemtClient("http://localhost", http_client=http, hooks=[Hook()]) as client:
            await asyncio.gather(client.users.list(), client.users.get("alice"))
    assert sorted(seen) == ["/v1/users", "/v1/users/alice"]


async def test_transport_failure_has_no_response_hook():
    from telemt import TransportError

    seen = []

    class Hook(ClientHook):
        async def on_response(self, response):
            seen.append(response)

    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with TelemtClient("http://localhost", http_client=http, hooks=[Hook()]) as client:
            with pytest.raises(TransportError):
                await client.health.get()
    assert seen == []


async def test_cancel_request_hook_prevents_send():
    entered = asyncio.Event()
    sent = []

    class Hook(ClientHook):
        async def on_request(self, request):
            entered.set()
            await asyncio.Event().wait()

    def handler(request):
        sent.append(request)
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with TelemtClient("http://localhost", http_client=http, hooks=[Hook()]) as client:
            task = asyncio.create_task(client.health.get())
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    assert sent == []
