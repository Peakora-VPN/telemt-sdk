"""Config state and preflight contracts from the Telemt 3.5.17 Rust source (66708d28).

Field presence mirrors serde omission: ``value`` and ``inherited_from`` on a
field row are skipped when unset, while nullable identities such as
``desired_revision`` or ``source_revision`` serialize even as JSON null.
"""

from pydantic import JsonValue

from .base import FieldIssue, ResponseModel
from .requests import ReloadRequest
from .responses import NormalizationEffect


class RuntimeBaseline(ResponseModel):
    """Identity of the runtime publication sampled by an inspection read."""

    active_generation: int
    config_epoch: int
    runtime_match: str


class FieldProjection(ResponseModel):
    """One redacted or public configuration path row in a projection.

    ``value`` is omitted unless the server judged the value safe to expose, so
    an explicit JSON null is distinguishable from omission through
    ``model_fields_set``. ``entries`` and ``differs`` serialize even when null.
    """

    path: str
    value: JsonValue | None = None
    redacted: bool
    present: bool
    entries: int | None = None
    differs: bool | None = None
    origin: str
    inherited_from: str | None = None


class ConfigProjection(ResponseModel):
    """Value-free bounded projection of one configuration snapshot."""

    fields: list[FieldProjection]
    truncated: bool
    provenance: str
    source_revision: str | None = None
    source_count: int | None = None


class ConfigComparison(ResponseModel):
    """Scoped differences between active, watcher, reload, and desired states."""

    scope: str
    status: str
    pending_paths: list[str]
    watcher_pending_paths: list[str]
    generation_pending_paths: list[str]
    process_deferred_paths: list[str]
    deferred_process_fields: list[str]
    runtime_derived_paths: list[str]
    truncated: bool


class WatchOutcome(ResponseModel):
    """Latest owner-authored watcher publication record."""

    sequence: int
    observed_at_epoch_secs: int
    phase: str
    source_revision: str | None = None
    published_config_epoch: int | None = None
    error_code: str | None = None


class ReloadObservation(ResponseModel):
    """Sanitized snapshot of the latest retained Maestro reload operation."""

    reload_id: int
    target_generation: int
    source_revision: str
    phase: str
    source_generation: int | None = None
    activated_generation: int | None = None
    retiring_generation: int | None = None
    retiring_config_epoch: int | None = None
    retirement: str | None = None
    error_present: bool
    warning_count: int


class ApplyImpact(ResponseModel):
    """Where a validated candidate applies and which boundary it must cross."""

    watcher_paths: list[str]
    generation_paths: list[str]
    process_restart_paths: list[str]
    restart_required: bool
    runtime_reload_required: bool
    process_restart_required: bool
    deferred_process_fields: list[str]


class ConfigStateData(ResponseModel):
    """Redacted comparison of the desired source and the effective publication.

    Envelope revision is the nullable ``desired_revision``; every optional
    member below serializes even as null except where the owning row documents
    serde omission.
    """

    scope: str
    sections: list[str]
    runtime: RuntimeBaseline
    runtime_sample_current: bool
    desired_revision: str | None = None
    desired_status: str
    desired_error: FieldIssue | None = None
    desired: ConfigProjection | None = None
    effective: ConfigProjection | None = None
    projection_error: FieldIssue | None = None
    comparison: ConfigComparison
    watcher: WatchOutcome | None = None
    watcher_matches_desired: bool | None = None
    reload: ReloadObservation | None = None
    reload_observation: str
    reload_matches_desired: bool | None = None
    subsystem_convergence: str


class ConfigValidationData(ResponseModel):
    """Preflight result for one candidate patch; nothing is persisted or reserved."""

    valid: bool
    base_revision: str
    candidate_revision: str
    runtime: RuntimeBaseline
    changed_paths: list[str]
    normalization_effects: list[NormalizationEffect]
    apply: ApplyImpact
    source_ownership: str
    touched_sections: list[str]
    reload: ReloadRequest | None = None
    warnings: list[FieldIssue]
