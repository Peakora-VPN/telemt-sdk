"""Discovery contracts from the Telemt 3.5.17 Rust source (66708d28).

API.md lists ``openapi_artifact`` on ``CapabilitiesData``, but the Rust DTO
never serializes it; unknown fields are preserved for forward compatibility.
"""

from pydantic import Field, JsonValue

from .base import ResponseModel


class OperationCapability(ResponseModel):
    """One operation with its gate, runtime availability, and mutation policy.

    ``available`` is null when an optional runtime source was not sampled or
    its lock was busy; the reason fields are omitted unless the server sets
    them. ``body`` names the request schema when the operation accepts one.
    """

    id: str
    method: str
    path: str
    aliases: list[str] = Field(default_factory=list)
    gate: str
    success: list[int]
    credential_bearing: bool = False
    body: str | None = None
    optional_body: bool = False
    exact_json_content_type: bool = False
    if_match: bool = False
    if_runtime_match: bool = False
    read_only_operation: bool = False
    supported: bool
    enabled: bool
    available: bool | None = None
    mutable: bool
    disabled_reason: str | None = None
    unavailable_reason: str | None = None
    mutation_blocked_reason: str | None = None


class CapabilitiesData(ResponseModel):
    """Implemented operations, feature gates, and runtime prerequisites."""

    api_version: str
    schema_version: int
    software_version: str
    config_schema: str
    read_only: bool
    availability_scope: str
    operations: list[OperationCapability]


class ApplyPolicy(ResponseModel):
    """How one configuration field reaches a running process."""

    watcher: str
    reload: str
    effect: str


class FieldApi(ResponseModel):
    """Which API views and mutations relate to one configuration field."""

    config_read: bool
    config_write: bool
    read_routes: list[str]
    write_routes: list[str]
    request_field: str | None = None
    non_editable_reason: str | None = None
    null_behavior: str


class FieldMetadata(ResponseModel):
    """One canonical configuration path with its schema and API metadata.

    ``default`` is omitted for ``required``, ``nested_fields``, ``map_entry``,
    and ``redacted`` default kinds; an explicit JSON null marks the ``unset``
    kind. Use ``model_fields_set`` to tell an omitted member from that null.
    """

    path: str
    value: JsonValue
    default_kind: str
    sensitivity: str
    description: str
    aliases: list[str] = Field(default_factory=list)
    unit: str | None = None
    apply: ApplyPolicy
    dependencies: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    default: JsonValue | None = None
    api: FieldApi


class ConfigPatchSemantics(ResponseModel):
    """Documented config PATCH semantics independent of any one field."""

    objects: str
    arrays: str
    object_null_members: str
    reset: str
    source_ownership: str
    if_match: str


class ConfigSchemaData(ResponseModel):
    """Checked metadata projection over unconfigured, typed configuration defaults."""

    schema_version: int
    value_schema_dialect: str
    defaults_scope: str
    validation_scope: str
    path_notation: str
    config_patch: ConfigPatchSemantics
    fields: list[FieldMetadata]
