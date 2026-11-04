"""Shared model configuration and HTTP response metadata."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ResponseModel(BaseModel):
    """Typed API data; preserve new server fields for forward compatibility."""

    model_config = ConfigDict(extra="allow", strict=True, hide_input_in_errors=True)


class APIResponse[T](ResponseModel):
    """One response and its own revision, safe to use with concurrent requests."""

    ok: Literal[True]
    data: T
    revision: str
    status_code: int = 200


class RequestModel(BaseModel):
    """Reject unknown inputs and keep omitted fields distinct from explicit null."""

    model_config = ConfigDict(
        extra="forbid", strict=True, revalidate_instances="always", hide_input_in_errors=True
    )


class ErrorDetail(ResponseModel):
    code: str
    message: str


class ErrorEnvelope(ResponseModel):
    ok: Literal[False]
    error: ErrorDetail
    request_id: int
