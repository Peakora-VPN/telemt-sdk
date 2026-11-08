"""Object-based hooks for SDK HTTP requests and responses."""

import httpx


class ClientHook:
    """Override either callback. Instances may be shared by concurrent requests.

    Callback errors propagate to the caller. Response callbacks run after the body
    is read and before API decoding, including HTTP error responses.
    """

    async def on_request(self, request: httpx.Request) -> None:
        """Called before sending a request."""

    async def on_response(self, response: httpx.Response) -> None:
        """Called after receiving a response."""
