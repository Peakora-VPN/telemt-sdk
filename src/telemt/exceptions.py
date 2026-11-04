"""Errors exposed by the SDK; cancellation is deliberately never intercepted."""


class TelemtError(Exception):
    """Base class for SDK failures."""


class TransportError(TelemtError):
    """The request could not complete; the original HTTPX error is the cause."""


class RequestTimeoutError(TransportError):
    """The request exceeded its configured HTTP timeout."""


class InvalidResponseError(TelemtError):
    """The server returned an invalid or incompatible API envelope."""

    def __init__(self, message: str, *, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(message)


class APIError(TelemtError):
    """A rejected API request, retaining its machine code and audit request ID."""

    def __init__(
        self, *, status_code: int, code: str, message: str, request_id: int | None = None
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.request_id = request_id
        super().__init__(f"HTTP {status_code} [{code}]: {message}")


class AuthenticationError(APIError):
    """Missing or invalid Authorization header (401)."""


class PermissionDeniedError(APIError):
    """The whitelist or read-only policy rejected the request (403)."""


class NotFoundError(APIError):
    """The requested resource does not exist (404)."""


class ConflictError(APIError):
    """A revision, runtime-instance, or operation conflict (409)."""
