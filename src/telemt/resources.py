"""Resource objects share the client transport and expose explicit async API methods."""

from __future__ import annotations

import asyncio
import math
from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from . import models as m

if TYPE_CHECKING:
    from .client import TelemtClient

_USERNAME = TypeAdapter(m.Username)
_SESSION_REF = TypeAdapter(m.SessionRef)
_OPERATION_REF = TypeAdapter(m.OperationRef)

_STATE_SECTIONS = frozenset(
    {
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
)


def _username(value: str) -> str:
    _USERNAME.validate_python(value, strict=True)
    # shortcut: dot-only names are normalized by HTTPX; support if Telemt adds URL decoding.
    if value in {".", ".."}:
        raise ValueError("dot-only usernames cannot safely be addressed by HTTPX")
    return value


class Resource:
    def __init__(self, client: TelemtClient) -> None:
        self._client = client


class HealthResource(Resource):
    async def get(self) -> m.APIResponse[m.HealthData]:
        """GET /v1/health."""
        return await self._client._request("GET", "health", m.APIResponse[m.HealthData])

    async def ready(self) -> m.APIResponse[m.HealthReadyData]:
        """GET /v1/health/ready."""
        return await self._client._request(
            "GET", "health/ready", m.APIResponse[m.HealthReadyData], accepted_statuses=(200, 503)
        )


class SystemResource(Resource):
    async def reload(
        self, request: m.ReloadRequest | None = None, *, revision: str | None = None
    ) -> m.APIResponse[m.ReloadAccepted]:
        """Submit an asynchronous runtime reload; poll reload_status for completion."""
        return await self._client._request(
            "POST",
            "system/reload",
            m.APIResponse[m.ReloadAccepted],
            body=request,
            revision=revision,
        )

    async def reload_status(self, reload_id: int) -> m.APIResponse[m.ReloadStatus]:
        if type(reload_id) is not int or not 0 <= reload_id < 2**64:
            raise ValueError("reload_id must be an unsigned 64-bit integer")
        return await self._client._request(
            "GET", f"system/reload/{reload_id}", m.APIResponse[m.ReloadStatus]
        )

    async def wait_reload(
        self,
        reload_id: int,
        *,
        timeout: float = 60,  # noqa: ASYNC109
        poll_interval: float = 1,
    ) -> m.APIResponse[m.ReloadStatus]:
        """Wait for a terminal status, including failure; raise TimeoutError on deadline."""
        _poll_limits(timeout, poll_interval)
        async with asyncio.timeout(timeout):
            while True:
                result = await self.reload_status(reload_id)
                if result.data.state in {"succeeded", "rolled_back", "failed"}:
                    return result
                await asyncio.sleep(poll_interval)

    async def info(self) -> m.APIResponse[m.SystemInfoData]:
        """GET /v1/system/info."""
        return await self._client._request("GET", "system/info", m.APIResponse[m.SystemInfoData])


class UsersResource(Resource):
    async def get(self, username: str) -> m.APIResponse[m.UserInfo]:
        return await self._client._request(
            "GET", f"users/{_username(username)}", m.APIResponse[m.UserInfo]
        )

    async def create(
        self, request: m.CreateUserRequest, *, revision: str | None = None
    ) -> m.APIResponse[m.CreateUserResponse]:
        _username(request.username)
        return await self._client._request(
            "POST", "users", m.APIResponse[m.CreateUserResponse], body=request, revision=revision
        )

    async def update(
        self, username: str, patch: m.PatchUserRequest, *, revision: str | None = None
    ) -> m.APIResponse[m.UserInfo]:
        return await self._client._request(
            "PATCH",
            f"users/{_username(username)}",
            m.APIResponse[m.UserInfo],
            body=patch,
            revision=revision,
        )

    async def delete(
        self, username: str, *, revision: str | None = None
    ) -> m.APIResponse[m.DeleteUserResponse]:
        return await self._client._request(
            "DELETE",
            f"users/{_username(username)}",
            m.APIResponse[m.DeleteUserResponse],
            revision=revision,
        )

    async def rotate_secret(
        self,
        username: str,
        request: m.RotateSecretRequest | None = None,
        *,
        revision: str | None = None,
    ) -> m.APIResponse[m.CreateUserResponse]:
        return await self._client._request(
            "POST",
            f"users/{_username(username)}/rotate-secret",
            m.APIResponse[m.CreateUserResponse],
            body=request,
            revision=revision,
        )

    async def enable(
        self, username: str, *, revision: str | None = None
    ) -> m.APIResponse[m.UserInfo]:
        return await self._client._request(
            "POST",
            f"users/{_username(username)}/enable",
            m.APIResponse[m.UserInfo],
            revision=revision,
        )

    async def disable(
        self, username: str, *, revision: str | None = None
    ) -> m.APIResponse[m.UserInfo]:
        return await self._client._request(
            "POST",
            f"users/{_username(username)}/disable",
            m.APIResponse[m.UserInfo],
            revision=revision,
        )

    async def reset_quota(
        self, username: str, *, revision: str | None = None
    ) -> m.APIResponse[m.ResetUserQuotaResponse]:
        return await self._client._request(
            "POST",
            f"users/{_username(username)}/reset-quota",
            m.APIResponse[m.ResetUserQuotaResponse],
            revision=revision,
        )

    async def list(self) -> m.APIResponse[list[m.UserInfo]]:
        """GET /v1/users."""
        return await self._client._request("GET", "users", m.APIResponse[list[m.UserInfo]])


class ConfigResource(Resource):
    async def update(
        self,
        patch: m.PatchConfigRequest,
        *,
        revision: str | None = None,
        runtime_match: str | None = None,
        reload: m.ReloadRequest | None = None,
    ) -> m.APIResponse[m.PatchConfigResponse]:
        return await self._client._request(
            "PATCH",
            "config",
            m.APIResponse[m.PatchConfigResponse],
            body=patch,
            params=_reload_params(reload),
            revision=revision,
            runtime_match=runtime_match,
        )

    async def get(self) -> m.APIResponse[m.ConfigData]:
        """GET /v1/config."""
        return await self._client._request("GET", "config", m.APIResponse[m.ConfigData])

    async def schema(self) -> m.APIResponse[m.ConfigSchemaData]:
        """GET /v1/config/schema."""
        return await self._client._request(
            "GET", "config/schema", m.APIResponse[m.ConfigSchemaData]
        )

    async def state(
        self, sections: Sequence[str] | None = None
    ) -> m.NullableRevisionAPIResponse[m.ConfigStateData]:
        """GET /v1/config/state; sections=None omits the query entirely.

        An empty selection is rejected, as are duplicate or unknown section
        names; the server never receives an empty ``sections`` value.
        """
        params = None
        if sections is not None:
            if isinstance(sections, str) or not sections:
                raise ValueError("sections must be a non-empty sequence of section names")
            names = list(sections)
            unknown = [name for name in names if name not in _STATE_SECTIONS]
            if unknown:
                raise ValueError(f"unknown config state sections: {unknown!r}")
            if len(set(names)) != len(names):
                raise ValueError("sections must not contain duplicate names")
            params = {"sections": ",".join(names)}
        return await self._client._request(
            "GET", "config/state", m.NullableRevisionAPIResponse[m.ConfigStateData], params=params
        )

    async def validate(
        self,
        patch: m.PatchConfigRequest,
        *,
        revision: str | None = None,
        runtime_match: str | None = None,
        reload: m.ReloadRequest | None = None,
    ) -> m.APIResponse[m.ConfigValidationData]:
        """POST /v1/config/validate; preflights a patch without persisting it."""
        return await self._client._request(
            "POST",
            "config/validate",
            m.APIResponse[m.ConfigValidationData],
            body=patch,
            params=_reload_params(reload),
            revision=revision,
            runtime_match=runtime_match,
        )


class DiscoveryResource(Resource):
    async def capabilities(self) -> m.APIResponse[m.CapabilitiesData]:
        """GET /v1/capabilities."""
        return await self._client._request("GET", "capabilities", m.APIResponse[m.CapabilitiesData])


class AccessResource(Resource):
    async def get(self) -> m.APIResponse[m.AccessPolicyData]:
        """GET /v1/access/policy."""
        return await self._client._request(
            "GET", "access/policy", m.APIResponse[m.AccessPolicyData]
        )

    async def update(
        self,
        patch: m.AccessPolicyPatch,
        *,
        revision: str | None = None,
        runtime_match: str | None = None,
    ) -> m.APIResponse[m.AccessPolicyData]:
        """PATCH /v1/access/policy; sparse nulls reset defaults or delete CIDR rules."""
        return await self._client._request(
            "PATCH",
            "access/policy",
            m.APIResponse[m.AccessPolicyData],
            body=patch,
            revision=revision,
            runtime_match=runtime_match,
        )


class LimitsResource(Resource):
    async def effective(self) -> m.APIResponse[m.EffectiveLimitsData]:
        """GET /v1/limits/effective."""
        return await self._client._request(
            "GET", "limits/effective", m.APIResponse[m.EffectiveLimitsData]
        )


class SecurityResource(Resource):
    async def posture(self) -> m.APIResponse[m.SecurityPostureData]:
        """GET /v1/security/posture."""
        return await self._client._request(
            "GET", "security/posture", m.APIResponse[m.SecurityPostureData]
        )

    async def whitelist(self) -> m.APIResponse[m.SecurityWhitelistData]:
        """GET /v1/security/whitelist."""
        return await self._client._request(
            "GET", "security/whitelist", m.APIResponse[m.SecurityWhitelistData]
        )


class StatsResource(Resource):
    async def summary(self) -> m.APIResponse[m.SummaryData]:
        """GET /v1/stats/summary."""
        return await self._client._request("GET", "stats/summary", m.APIResponse[m.SummaryData])

    async def zero_all(self) -> m.APIResponse[m.ZeroAllData]:
        """GET /v1/stats/zero/all."""
        return await self._client._request("GET", "stats/zero/all", m.APIResponse[m.ZeroAllData])

    async def upstreams(self) -> m.APIResponse[m.UpstreamsData]:
        """GET /v1/stats/upstreams."""
        return await self._client._request("GET", "stats/upstreams", m.APIResponse[m.UpstreamsData])

    async def minimal_all(self) -> m.APIResponse[m.MinimalAllData]:
        """GET /v1/stats/minimal/all."""
        return await self._client._request(
            "GET", "stats/minimal/all", m.APIResponse[m.MinimalAllData]
        )

    async def me_writers(self) -> m.APIResponse[m.MeWritersData]:
        """GET /v1/stats/me-writers."""
        return await self._client._request(
            "GET", "stats/me-writers", m.APIResponse[m.MeWritersData]
        )

    async def dcs(self) -> m.APIResponse[m.DcStatusData]:
        """GET /v1/stats/dcs."""
        return await self._client._request("GET", "stats/dcs", m.APIResponse[m.DcStatusData])

    async def users(self) -> m.APIResponse[list[m.UserInfo]]:
        """GET /v1/stats/users."""
        return await self._client._request("GET", "stats/users", m.APIResponse[list[m.UserInfo]])

    async def active_ips(self) -> m.APIResponse[list[m.UserActiveIps]]:
        """GET /v1/stats/users/active-ips."""
        return await self._client._request(
            "GET", "stats/users/active-ips", m.APIResponse[list[m.UserActiveIps]]
        )

    async def quota(self) -> m.APIResponse[m.UserQuotaData]:
        """GET /v1/stats/users/quota."""
        return await self._client._request(
            "GET", "stats/users/quota", m.APIResponse[m.UserQuotaData]
        )


class RuntimeResource(Resource):
    def __init__(self, client: TelemtClient) -> None:
        super().__init__(client)
        self.web = WebResource(client)

    async def events_recent(
        self, *, limit: int | None = None
    ) -> m.APIResponse[m.RuntimeEdgeEventsData]:
        return await self._client._request(
            "GET",
            "runtime/events/recent",
            m.APIResponse[m.RuntimeEdgeEventsData],
            params=_limit(limit),
        )

    async def tls_fingerprints(
        self, *, limit: int | None = None
    ) -> m.APIResponse[m.RuntimeEdgeTlsFingerprintsData]:
        return await self._client._request(
            "GET",
            "runtime/tls-fingerprints",
            m.APIResponse[m.RuntimeEdgeTlsFingerprintsData],
            params=_limit(limit),
        )

    async def gates(self) -> m.APIResponse[m.RuntimeGatesData]:
        """GET /v1/runtime/gates."""
        return await self._client._request(
            "GET", "runtime/gates", m.APIResponse[m.RuntimeGatesData]
        )

    async def initialization(self) -> m.APIResponse[m.RuntimeInitializationData]:
        """GET /v1/runtime/initialization."""
        return await self._client._request(
            "GET", "runtime/initialization", m.APIResponse[m.RuntimeInitializationData]
        )

    async def me_pool_state(self) -> m.APIResponse[m.RuntimeMePoolStateData]:
        """GET /v1/runtime/me_pool_state."""
        return await self._client._request(
            "GET", "runtime/me_pool_state", m.APIResponse[m.RuntimeMePoolStateData]
        )

    async def me_quality(self) -> m.APIResponse[m.RuntimeMeQualityData]:
        """GET /v1/runtime/me_quality."""
        return await self._client._request(
            "GET", "runtime/me_quality", m.APIResponse[m.RuntimeMeQualityData]
        )

    async def upstream_quality(self) -> m.APIResponse[m.RuntimeUpstreamQualityData]:
        """GET /v1/runtime/upstream_quality."""
        return await self._client._request(
            "GET", "runtime/upstream_quality", m.APIResponse[m.RuntimeUpstreamQualityData]
        )

    async def nat_stun(self) -> m.APIResponse[m.RuntimeNatStunData]:
        """GET /v1/runtime/nat_stun."""
        return await self._client._request(
            "GET", "runtime/nat_stun", m.APIResponse[m.RuntimeNatStunData]
        )

    async def me_selftest(self) -> m.APIResponse[m.RuntimeMeSelftestData]:
        """GET /v1/runtime/me-selftest."""
        return await self._client._request(
            "GET", "runtime/me-selftest", m.APIResponse[m.RuntimeMeSelftestData]
        )

    async def connections_summary(self) -> m.APIResponse[m.RuntimeEdgeConnectionsSummaryData]:
        """GET /v1/runtime/connections/summary."""
        return await self._client._request(
            "GET", "runtime/connections/summary", m.APIResponse[m.RuntimeEdgeConnectionsSummaryData]
        )


class WebResource(Resource):
    async def sessions(self, query: m.SessionQuery | None = None) -> m.APIResponse[m.SessionPage]:
        if query is not None:
            query = m.SessionQuery.model_validate(query)
        return await self._client._request(
            "GET",
            "runtime/web/sessions",
            m.APIResponse[m.SessionPage],
            params=query.model_dump(exclude_none=True) if query is not None else None,
        )

    async def iter_sessions(
        self, query: m.SessionQuery | None = None
    ) -> AsyncIterator[m.SessionRow]:
        """Yield sessions across pages; use sessions() to inspect snapshot metadata."""
        query = m.SessionQuery.model_validate(query or m.SessionQuery()).model_copy(deep=True)
        seen = {query.cursor} if query.cursor is not None else set()
        while True:
            page = await self.sessions(query)
            for session in page.data.sessions:
                yield session
            cursor = page.data.next_cursor
            if cursor is None:
                return
            if cursor in seen:
                raise ValueError("server returned a repeated session cursor")
            seen.add(cursor)
            query = m.SessionQuery.model_validate(query.model_dump() | {"cursor": cursor})

    async def session(self, session_ref: str) -> m.APIResponse[m.GoneSessionData | m.SessionRow]:
        return await self._client._request(
            "GET",
            f"runtime/web/sessions/{_SESSION_REF.validate_python(session_ref, strict=True)}",
            m.APIResponse[m.GoneSessionData | m.SessionRow],
            accepted_statuses=(200, 410),
        )

    async def close_sessions(
        self, request: m.CloseRequest
    ) -> m.APIResponse[m.ControlOperationStatus]:
        return await self._client._request(
            "POST",
            "runtime/web/sessions/close",
            m.APIResponse[m.ControlOperationStatus],
            body=request,
        )

    async def operation(self, operation_id: str) -> m.APIResponse[m.ControlOperationStatus]:
        return await self._client._request(
            "GET",
            f"runtime/web/operations/{_OPERATION_REF.validate_python(operation_id, strict=True)}",
            m.APIResponse[m.ControlOperationStatus],
        )

    async def wait_operation(
        self,
        operation_id: str,
        *,
        timeout: float = 60,  # noqa: ASYNC109
        poll_interval: float = 1,
    ) -> m.APIResponse[m.ControlOperationStatus]:
        """Wait for a terminal state: completed, failed, or cancelled."""
        _poll_limits(timeout, poll_interval)
        async with asyncio.timeout(timeout):
            while True:
                result = await self.operation(operation_id)
                if result.data.state in {"completed", "failed", "cancelled"}:
                    return result
                await asyncio.sleep(poll_interval)

    async def clear_debug(
        self, request: m.RuntimeInstanceRequest
    ) -> m.APIResponse[m.DebugClearData]:
        return await self._client._request(
            "POST", "runtime/web/debug/clear", m.APIResponse[m.DebugClearData], body=request
        )

    async def reset_carrier_learning(
        self, request: m.RuntimeInstanceRequest
    ) -> m.APIResponse[m.LearningResetData]:
        return await self._client._request(
            "POST",
            "runtime/web/carrier-learning/reset",
            m.APIResponse[m.LearningResetData],
            body=request,
        )

    async def pause(
        self, request: m.RuntimeInstanceRequest
    ) -> m.APIResponse[m.OperatorLifecycleStatus]:
        return await self._client._request(
            "POST",
            "runtime/web/lifecycle/pause",
            m.APIResponse[m.OperatorLifecycleStatus],
            body=request,
        )

    async def drain(self, request: m.DrainRequest) -> m.APIResponse[m.OperatorLifecycleStatus]:
        return await self._client._request(
            "POST",
            "runtime/web/lifecycle/drain",
            m.APIResponse[m.OperatorLifecycleStatus],
            body=request,
        )

    async def resume(
        self, request: m.RuntimeInstanceRequest
    ) -> m.APIResponse[m.OperatorLifecycleStatus]:
        return await self._client._request(
            "POST",
            "runtime/web/lifecycle/resume",
            m.APIResponse[m.OperatorLifecycleStatus],
            body=request,
        )

    async def status(self) -> m.APIResponse[m.WebStatusData]:
        """GET /v1/runtime/web/status."""
        return await self._client._request(
            "GET", "runtime/web/status", m.APIResponse[m.WebStatusData]
        )


def _limit(value: int | None) -> dict[str, int] | None:
    if value is None:
        return None
    if type(value) is not int or not 1 <= value <= 1000:
        raise ValueError("limit must be an integer between 1 and 1000")
    return {"limit": value}


def _reload_params(reload: m.ReloadRequest | None) -> dict[str, str | int] | None:
    if reload is None:
        return None
    reload = m.ReloadRequest.model_validate(reload)
    params = reload.model_dump(exclude_none=True)
    params["reload"] = params.pop("mode")
    return params


def _poll_limits(timeout: float, poll_interval: float) -> None:
    for name, value in (("timeout", timeout), ("poll_interval", poll_interval)):
        if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
