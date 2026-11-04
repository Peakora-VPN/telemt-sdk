import httpx
import pytest

from telemt import TelemtClient


@pytest.fixture
def user_data():
    return {
        "username": "alice",
        "enabled": True,
        "in_runtime": False,
        "current_connections": 0,
        "active_unique_ips": 0,
        "active_unique_ips_list": [],
        "recent_unique_ips": 0,
        "recent_unique_ips_list": [],
        "total_octets": 0,
        "links": {"classic": [], "secure": [], "tls": [], "tls_domains": []},
    }


@pytest.fixture
async def mock_api():
    """Exercise real HTTPX requests and parsing without network access."""
    requests = []
    responses = []

    def handler(request):
        requests.append(request)
        assert responses, "Unexpected request"
        return responses.pop(0)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with TelemtClient(
            "http://localhost:9091", auth_header="exact auth value", http_client=http
        ) as client:
            yield client, requests, responses


def success(data, *, status=200, revision="a" * 64):
    return httpx.Response(status, json={"ok": True, "data": data, "revision": revision})
