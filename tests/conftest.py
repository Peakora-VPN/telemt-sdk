import httpx
import pytest

from telemt import TelemtClient


@pytest.fixture
def user_data():
    unlimited = {
        "value": None,
        "configured_override": None,
        "global_value": 0,
        "origin": "unlimited",
    }
    return {
        "username": "alice",
        "enabled": True,
        "in_runtime": False,
        "limits": {
            "desired": {"max_tcp_conns": unlimited, "max_unique_ips": unlimited},
            "effective": None,
            "effective_scope": "active_config_snapshot",
            "subsystem_convergence": "unknown",
        },
        "source_deny": [],
        "source_deny_status": {
            "effective": None,
            "runtime_reload_required": None,
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
