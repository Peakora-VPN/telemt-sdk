"""An asynchronous, connection-pooling Telemt Control API client."""

from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import Self

import httpx
from pydantic import ValidationError

from .exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    InvalidResponseError,
    NotFoundError,
    PermissionDeniedError,
    RequestTimeoutError,
    TransportError,
)
from .hooks import ClientHook
from .models.base import (
    APIEnvelopeBase,
    ErrorEnvelope,
    RequestModel,
)
from .models.requests import (
    AccessPolicyPatch,
    CreateUserRequest,
    PatchConfigRequest,
    PatchUserRequest,
)
from .resources import (
    AccessResource,
    ConfigResource,
    DiscoveryResource,
    HealthResource,
    LimitsResource,
    RuntimeResource,
    SecurityResource,
    StatsResource,
    SystemResource,
    UsersResource,
)

_RUNTIME_MATCH_CHARACTERS = frozenset("0123456789abcdefABCDEF:")
_RUNTIME_MATCH_MAX_LENGTH = 128


def _validate_runtime_match(runtime_match: str) -> str:
    if (
        not isinstance(runtime_match, str)
        or not runtime_match
        or len(runtime_match) > _RUNTIME_MATCH_MAX_LENGTH
        or any(character not in _RUNTIME_MATCH_CHARACTERS for character in runtime_match)
    ):
        raise ValueError("runtime_match must be 1-128 characters limited to hex digits and colons")
    return runtime_match


class TelemtClient:
    """Use as an async context manager, or call aclose() explicitly.

    auth_header is the exact Authorization value configured by Telemt.
    An injected HTTPX client remains owned by the caller.
    """

    def __init__(
        self,
        base_url: str,
        *,
        auth_header: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        http_client: httpx.AsyncClient | None = None,
        hooks: Sequence[ClientHook] = (),
    ) -> None:
        url = httpx.URL(base_url)
        if url.scheme not in {"http", "https"} or not url.host:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if url.query or url.fragment or url.userinfo:
            raise ValueError("base_url must not contain credentials, a query, or a fragment")
        path = url.path.rstrip("/")
        if not path.endswith("/v1"):
            path += "/v1"
        self._base_url = url.copy_with(path=path + "/")
        self._headers = {"Accept": "application/json"}
        if auth_header is not None:
            self._headers["Authorization"] = auth_header
        self._hooks = tuple(hooks)
        self._timeout = timeout
        self._owns_http_client = http_client is None
        self._http = http_client if http_client is not None else httpx.AsyncClient()
        self._closed = False
        self.health = HealthResource(self)
        self.system = SystemResource(self)
        self.users = UsersResource(self)
        self.config = ConfigResource(self)
        self.discovery = DiscoveryResource(self)
        self.access = AccessResource(self)
        self.stats = StatsResource(self)
        self.runtime = RuntimeResource(self)
        self.security = SecurityResource(self)
        self.limits = LimitsResource(self)

    async def __aenter__(self) -> Self:
        if self._closed:
            raise RuntimeError("TelemtClient is closed")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close owned connections; safe to call more than once."""
        if not self._closed:
            if self._owns_http_client:
                await self._http.aclose()
            self._closed = True

    async def _request[T, E: APIEnvelopeBase](
        self,
        method: str,
        path: str,
        response_type: type[E],
        *,
        body: RequestModel | None = None,
        params: Mapping[str, str | int] | None = None,
        revision: str | None = None,
        runtime_match: str | None = None,
        accepted_statuses: tuple[int, ...] = (200, 201, 202),
    ) -> E:
        if self._closed:
            raise RuntimeError("TelemtClient is closed")
        headers = self._headers.copy()
        if revision is not None:
            headers["If-Match"] = revision
        if runtime_match is not None:
            headers["If-Runtime-Match"] = _validate_runtime_match(runtime_match)
        payload = None
        if body is not None:
            body = type(body).model_validate(body)
            headers["Content-Type"] = "application/json"
            # Sparse bodies keep omitted fields absent and send explicit nulls.
            is_sparse = isinstance(
                body, (AccessPolicyPatch, CreateUserRequest, PatchConfigRequest, PatchUserRequest)
            )
            payload = body.model_dump(
                mode="json", exclude_unset=is_sparse, exclude_none=not is_sparse, by_alias=True
            )
        url = self._base_url.join(path).copy_with(params=params)
        request = self._http.build_request(
            method,
            url,
            headers=headers,
            json=payload,
            timeout=self._timeout,
        )
        # Client defaults must not add query fields or replace exact Telemt authorization.
        request.url = url
        for hook in self._hooks:
            await hook.on_request(request)
        try:
            response = await self._http.send(request, auth=None, follow_redirects=False)
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError("Telemt request timed out") from exc
        except httpx.RequestError as exc:
            raise TransportError("Telemt request failed") from exc

        for hook in self._hooks:
            await hook.on_response(response)

        try:
            envelope = response.json()
        except ValueError as exc:
            raise InvalidResponseError(
                "Telemt returned invalid JSON", status_code=response.status_code
            ) from exc
        if not isinstance(envelope, dict) or type(envelope.get("ok")) is not bool:
            raise InvalidResponseError(
                "Telemt returned an invalid envelope", status_code=response.status_code
            )
        if envelope["ok"] is False:
            try:
                error = ErrorEnvelope.model_validate(envelope)
            except ValidationError as exc:
                raise InvalidResponseError(
                    "Telemt returned an invalid error envelope", status_code=response.status_code
                ) from exc
            error_type = {
                401: AuthenticationError,
                403: PermissionDeniedError,
                404: NotFoundError,
                409: ConflictError,
            }.get(response.status_code, APIError)
            raise error_type(
                status_code=response.status_code,
                code=error.error.code,
                message=error.error.message,
                request_id=error.request_id,
                details=error.error.details,
            )
        if response.status_code not in accepted_statuses:
            raise APIError(
                status_code=response.status_code,
                code="unexpected_http_status",
                message="Success envelope received with an unexpected HTTP status",
            )
        try:
            parsed = response_type.model_validate_json(response.content)
            parsed.status_code = response.status_code
            return parsed
        except ValidationError as exc:
            raise InvalidResponseError(
                "Telemt response does not match the API contract", status_code=response.status_code
            ) from exc
