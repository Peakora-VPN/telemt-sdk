"""Validated request objects, including sparse JSON Merge Patch semantics."""

import calendar
import re
from ipaddress import IPv6Address, ip_address
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, JsonValue, field_validator, model_validator

from .base import RequestModel

type Username = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,64}$")]
type Hex32 = Annotated[str, Field(pattern=r"^[A-Fa-f0-9]{32}$")]
type UInt64 = Annotated[int, Field(ge=0, le=2**64 - 1)]
type DrainTimeout = Annotated[int, Field(ge=1, le=3600)]
type QuotaPeriod = Literal["daily", "weekly", "monthly"]
type RuntimeInstance = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


def _nonzero_reference(value: str) -> str:
    if value.endswith(".0000000000000000"):
        raise ValueError("runtime reference ID must be nonzero")
    return value


type SessionRef = Annotated[
    str, Field(pattern=r"^ws1\.[a-f0-9]{32}\.[a-f0-9]{16}$"), AfterValidator(_nonzero_reference)
]
type OperationRef = Annotated[
    str, Field(pattern=r"^wo1\.[a-f0-9]{32}\.[a-f0-9]{16}$"), AfterValidator(_nonzero_reference)
]
type Carrier = Literal["https", "https-lanes", "websocket", "websocket-lanes"]
type SessionState = Literal[
    "provisional", "replacing", "committed", "healthy", "closing", "superseded", "closed"
]

_RFC3339 = re.compile(
    r"[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])[Tt ]"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:(?:[0-5][0-9]|60)(?:\.[0-9]+)?"
    r"(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


class UserOptions(RequestModel):
    user_ad_tag: Hex32 | None = None
    max_tcp_conns: UInt64 | None = None
    expiration_rfc3339: str | None = None
    data_quota_bytes: UInt64 | None = None
    quota_period: QuotaPeriod | None = None
    rate_limit_up_bps: UInt64 | None = None
    rate_limit_down_bps: UInt64 | None = None
    max_unique_ips: UInt64 | None = None
    enabled: bool | None = None

    @field_validator("expiration_rfc3339")
    @classmethod
    def valid_expiration(cls, value: str | None) -> str | None:
        if value is not None:
            if not _RFC3339.fullmatch(value):
                raise ValueError("expiration_rfc3339 must be valid RFC3339")
            # Chrono accepts year 0000 and leap seconds, which datetime cannot represent.
            days = calendar.monthrange(int(value[:4]), int(value[5:7]))[1]
            if int(value[8:10]) > days:
                raise ValueError("expiration_rfc3339 contains an invalid calendar date")
        return value


class CreateUserRequest(UserOptions):
    username: Username
    secret: Hex32 | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def recurring_quota(self) -> Self:
        if self.quota_period is not None and not self.data_quota_bytes:
            raise ValueError("quota_period requires positive data_quota_bytes")
        return self


class PatchUserRequest(UserOptions):
    """Omitted fields stay unchanged; None clears overrides but leaves secret unchanged."""

    secret: Hex32 | None = Field(default=None, repr=False)


class RotateSecretRequest(RequestModel):
    secret: Hex32 | None = Field(default=None, repr=False)


class PatchConfigRequest(RequestModel):
    general: dict[str, JsonValue] | None = None
    timeouts: dict[str, JsonValue] | None = None
    censorship: dict[str, JsonValue] | None = None
    upstreams: list[dict[str, JsonValue]] | None = None
    dc_overrides: dict[str, JsonValue] | None = None
    web: dict[str, JsonValue] | None = None
    server: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def editable_sections(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("config patch must contain an editable section")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("config sections cannot be null")
        if self.server is not None and (not self.server or self.server.keys() - {"listeners"}):
            raise ValueError("only server.listeners is editable")
        return self


class ReloadRequest(RequestModel):
    mode: Literal["instant", "drain"] = "instant"
    timeout_secs: DrainTimeout | None = None
    failure_policy: Literal["keep_new", "rollback"] = "keep_new"

    @model_validator(mode="after")
    def drain_timeout(self) -> Self:
        if (self.mode == "drain") != (self.timeout_secs is not None):
            raise ValueError("timeout_secs is required for drain and forbidden for instant")
        return self


class SessionFilter(RequestModel):
    session_ref: SessionRef | None = None
    ip: str | None = None
    host: str | None = None
    user: str | None = None
    user_agent_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")] | None = None
    key_id: Annotated[str, Field(pattern=r"^[a-f0-9]{16}$")] | None = None
    carrier: Carrier | None = None
    state: SessionState | None = None

    @field_validator("ip")
    @classmethod
    def canonical_ip(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = ip_address(value)
            canonical = str(parsed)
            if isinstance(parsed, IPv6Address) and parsed.ipv4_mapped is not None:
                canonical = f"::ffff:{parsed.ipv4_mapped}"
            if "%" in value or canonical != value:
                raise ValueError("ip must use canonical IPv4 or IPv6 formatting")
        return value

    @field_validator("host", "user")
    @classmethod
    def nonempty(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("filter cannot be empty")
        return value

    @model_validator(mode="after")
    def byte_limits(self) -> Self:
        for name, limit in (("host", 253), ("user", 64)):
            value = getattr(self, name)
            if value is not None and len(value.encode("utf-8")) > limit:
                raise ValueError(f"{name} exceeds {limit} bytes")
        return self


class SessionQuery(SessionFilter):
    limit: Annotated[int, Field(ge=1, le=200)] | None = None
    cursor: SessionRef | None = None

    @model_validator(mode="after")
    def exact_lookup(self) -> Self:
        if self.session_ref is not None and (self.limit is not None or self.cursor is not None):
            raise ValueError("session_ref cannot be combined with limit or cursor")
        return self


class RefsSelector(RequestModel):
    kind: Literal["refs"] = "refs"
    session_refs: Annotated[list[SessionRef], Field(min_length=1, max_length=200)]

    @field_validator("session_refs")
    @classmethod
    def unique_refs(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("session_refs must be unique")
        return value


class FilterSelector(SessionFilter):
    kind: Literal["filter"] = "filter"

    @model_validator(mode="after")
    def has_filter(self) -> Self:
        if not any(getattr(self, name) is not None for name in SessionFilter.model_fields):
            raise ValueError("filter selector requires at least one filter")
        return self


class AllSelector(RequestModel):
    kind: Literal["all"] = "all"


class RuntimeInstanceRequest(RequestModel):
    runtime_instance: RuntimeInstance


class DrainRequest(RuntimeInstanceRequest):
    timeout_secs: DrainTimeout


class CloseRequest(RuntimeInstanceRequest):
    selector: Annotated[RefsSelector | FilterSelector | AllSelector, Field(discriminator="kind")]

    @model_validator(mode="after")
    def matching_instance(self) -> Self:
        refs = []
        if isinstance(self.selector, RefsSelector):
            refs = self.selector.session_refs
        elif isinstance(self.selector, FilterSelector) and self.selector.session_ref:
            refs = [self.selector.session_ref]
        if any(ref.split(".")[1] != self.runtime_instance for ref in refs):
            raise ValueError("session reference belongs to another runtime_instance")
        return self
