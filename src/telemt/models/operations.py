"""Reload and quota contracts."""

from pydantic import Field

from .base import ResponseModel


class ReloadAccepted(ResponseModel):
    reload_id: int
    target_generation: int
    config_revision: str
    state: str
    mode: str
    failure_policy: str


class ReloadStatus(ReloadAccepted):
    requested_at_epoch_secs: int
    started_at_epoch_secs: int | None = None
    finished_at_epoch_secs: int | None = None
    deferred_process_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class UserQuota(ResponseModel):
    username: str
    data_quota_bytes: int
    used_bytes: int
    last_reset_epoch_secs: int
    quota_period: str | None = None
    active_quota_period: str | None = None
    quota_period_start_epoch_secs: int | None = None
    quota_next_reset_epoch_secs: int | None = None
    quota_schedule_state: str


class UserQuotaData(ResponseModel):
    users: list[UserQuota]
