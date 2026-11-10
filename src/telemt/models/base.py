"""Shared model configuration and HTTP response metadata."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResponseModel(BaseModel):
    """Typed API data; preserve new server fields for forward compatibility."""

    model_config = ConfigDict(extra="allow", strict=True, hide_input_in_errors=True)


class APIEnvelopeBase(ResponseModel):
    """Success-envelope metadata shared by every revision flavor."""

    ok: Literal[True]
    status_code: int = 200


class APIResponse[T](APIEnvelopeBase):
    """One response and its own revision, safe to use with concurrent requests."""

    data: T
    revision: str


class NullableRevisionAPIResponse[T](APIEnvelopeBase):
    """Success envelope whose revision the server may omit (for example config/state)."""

    data: T
    revision: str | None


class RequestModel(BaseModel):
    """Reject unknown inputs and keep omitted fields distinct from explicit null."""

    model_config = ConfigDict(
        extra="forbid", strict=True, revalidate_instances="always", hide_input_in_errors=True
    )


class FieldIssue(BaseModel):
    """One structured invalid-field report attached to a rejected request.

    Kept off ResponseModel so the Rust source inventory stays the single
    authority on serialized DTOs; configuration mirrors ResponseModel.
    """

    model_config = ConfigDict(extra="allow", strict=True, hide_input_in_errors=True)

    path: str
    code: str
    message: str


class ErrorDetail(ResponseModel):
    code: str
    message: str
    details: list[FieldIssue] = Field(default_factory=list)


class ErrorEnvelope(ResponseModel):
    ok: Literal[False]
    error: ErrorDetail
    request_id: int
