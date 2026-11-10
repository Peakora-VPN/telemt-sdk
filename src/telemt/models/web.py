"""Complete WEB control-plane response models for Telemt 3.5.17 (66708d28)."""

from .base import ResponseModel


class WebIngressStatus(ResponseModel):
    """Serialized by `src/api/web_runtime/observability.rs`."""

    configured_listeners: int
    live_acceptors: int
    accepting_connections: bool
    reason: str | None = None
    tcp_accept_total: int
    tcp_accept_error_total: int


class WebCapacityResourceStatus(ResponseModel):
    """Serialized by `src/web/manager/observability.rs`."""

    resource: str
    unit: str
    used: int
    available: int
    limit: int
    closed: bool


class WebRejectionCounter(ResponseModel):
    """Serialized by `src/web/telemetry.rs`."""

    reason: str
    total: int


class WebOutcomeCounter(ResponseModel):
    """Serialized by `src/web/telemetry.rs`."""

    outcome: str
    total: int


class WebCapacityStatus(ResponseModel):
    """Serialized by `src/api/web_runtime/observability.rs`."""

    http_connection_capacity_action: str
    max_http_overload_connections: int
    http_overload_timeout_ms: int
    resources: list[WebCapacityResourceStatus]
    saturated_resources: list[str]
    partial: list[str]
    rejections: list[WebRejectionCounter]
    http_connection_overload_outcomes: list[WebOutcomeCounter]


class WebDecoyUpstreamStatus(ResponseModel):
    """Serialized by `src/api/web_runtime/observability.rs`."""

    outcomes: list[WebOutcomeCounter]
    last_outcome: str | None = None
    last_outcome_age_ms: int | None = None


class WebDecoyFastTrackCounter(ResponseModel):
    """Serialized by `src/web/telemetry/fasttrack.rs`."""

    disposition: str
    total: int


class WebDecoyFastTrackStatus(ResponseModel):
    """Serialized by `src/api/web_runtime/observability.rs`."""

    mode: str
    requests: list[WebDecoyFastTrackCounter]


class WebCarrierSelectionCounter(ResponseModel):
    """Serialized by `src/web/telemetry/carrier.rs`."""

    carrier: str
    disposition: str
    total: int


class WebCarrierFailureCounter(ResponseModel):
    """Serialized by `src/web/telemetry/carrier.rs`."""

    carrier: str
    phase: str
    reason: str
    total: int


class WebCarrierLearningCounter(ResponseModel):
    """Serialized by `src/web/telemetry/carrier.rs`."""

    carrier: str
    outcome: str
    total: int


class WebCarrierNegotiationStatus(ResponseModel):
    """Serialized by `src/api/web_runtime/observability.rs`."""

    selections: list[WebCarrierSelectionCounter]
    reported_failures: list[WebCarrierFailureCounter]
    learning_outcomes: list[WebCarrierLearningCounter]


class WebSessionCloseCounter(ResponseModel):
    """Serialized by `src/web/telemetry/lifecycle.rs`."""

    carrier: str
    reason: str
    total: int


class WebSessionLifecycleObservationCounter(ResponseModel):
    """Serialized by `src/web/telemetry/lifecycle.rs`."""

    carrier: str
    observation: str
    total: int


class WebBridgeRecoveryCounter(ResponseModel):
    """Serialized by `src/web/telemetry/lifecycle.rs`."""

    event: str
    total: int


class WebLifecycleCountersStatus(ResponseModel):
    """Serialized by `src/api/web_runtime/observability.rs`."""

    bridge_recovery_secs: int
    session_closures: list[WebSessionCloseCounter]
    session_observations: list[WebSessionLifecycleObservationCounter]
    bridge_recovery_events: list[WebBridgeRecoveryCounter]


class OperatorDrainStatus(ResponseModel):
    """Serialized by `src/web/manager/operator_lifecycle/status.rs`."""

    operation_id: str
    state: str
    outcome: str | None = None
    timeout_secs: int
    started_epoch_millis: int
    deadline_epoch_millis: int
    completed_epoch_millis: int | None = None
    remaining_sessions: int
    remaining_streams: int
    remaining_websockets: int
    force_close_signalled: bool


class OperatorLifecycleStatus(ResponseModel):
    """Serialized by `src/web/manager/operator_lifecycle/status.rs`."""

    state: str
    epoch: int
    age_ms: int
    admission_open: bool
    effective_new_work_admission: bool
    drain: OperatorDrainStatus | None = None


class WebWildcardLimitsConfig(ResponseModel):
    """Serialized by `src/config/types/web/wildcard.rs`."""

    max_rules: int
    max_profiles_per_request: int
    cache_hosts: int
    cache_bytes: int
    cold_hmac_per_minute: int
    cold_hmac_burst: int


class WebLimitsConfig(ResponseModel):
    """Serialized by `src/config/types/web.rs`."""

    wildcard: WebWildcardLimitsConfig
    max_header_bytes: int
    max_body_bytes: int
    max_frame_payload_bytes: int
    carrier_batch_bytes: int
    max_frames_per_body: int
    max_http_connections: int
    max_http_overload_connections: int
    max_http_handlers: int
    max_lane_open_waits_per_session: int
    pending_bytes_per_lane: int
    pending_items_per_lane: int
    websocket_bytes_global: int
    websocket_admission_watermark_pct: int
    websocket_eviction_watermark_pct: int
    websocket_http_connection_reserve: int
    max_websocket_evictions_in_flight: int
    max_carrier_learning_entries: int
    max_body_readers: int
    max_body_bytes_global: int
    max_sessions_global: int
    max_sessions_per_ip: int
    max_streams_per_session: int
    max_streams_global: int
    max_stream_handshakes: int
    max_tombstones_per_session: int
    pending_bytes_per_session: int
    pending_bytes_global: int
    pending_items_per_session: int
    pending_items_global: int
    control_bytes_per_session: int
    control_bytes_global: int
    max_bootstraps_global: int
    max_bootstraps_per_ip: int
    max_vhosts: int
    max_profiles: int
    max_static_files: int
    max_static_file_bytes: int
    max_static_bytes: int
    debug_records_capacity: int
    debug_bytes_global: int
    memory_envelope_bytes: int
    new_bootstraps_per_minute: int
    new_bootstraps_burst: int
    new_sessions_per_minute: int
    new_sessions_burst: int
    new_streams_per_minute: int
    new_streams_burst: int


class WebManagerStatus(ResponseModel):
    """Serialized by `src/web/manager/status.rs`."""

    issuance_enabled: bool
    issuance_generation: int
    shutdown: bool
    bootstraps: int
    sessions: int
    closed_tokens: int
    closed_sessions: int
    client_ips: int
    profiles: int


class WebStreamStatus(ResponseModel):
    """Serialized by `src/web/manager/status.rs`."""

    live: int
    profiles: int
    closed: bool


class WebBudgetStatus(ResponseModel):
    """Serialized by `src/web/manager/status.rs`."""

    queue_bytes: int
    queue_items: int
    control_bytes: int
    control_items: int
    websocket_bytes: int
    high_water_bytes: int
    owners: int
    closed: bool


class WebSocketStatus(ResponseModel):
    """Serialized by `src/web/manager/status.rs`."""

    entries: int
    claims: int
    evictions_in_flight: int
    closed: bool


class WebLearningStatus(ResponseModel):
    """Serialized by `src/web/manager/status.rs`."""

    enabled: bool
    aggressiveness: str
    policy_generation: int | None = None
    epoch: int | None = None
    entries: int
    capacity: int
    lifetime_secs: int
    health_secs: int
    age_ms: int


class WebDebugConfig(ResponseModel):
    """Serialized by `src/config/types/web_debug.rs`."""

    enabled: bool
    sideband: bool
    capture_lifecycle: bool
    capture_headers: bool
    capture_timings: bool
    capture_frames: bool
    body_capture: str
    body_prefix_bytes: int
    decoy_body_prefix_bytes: int
    default_window_secs: int
    max_window_secs: int


class WebDebugStatus(ResponseModel):
    """Serialized by `src/web/manager/status.rs`."""

    policy: WebDebugConfig
    policy_generation: int
    epoch: int
    records: int
    records_capacity: int
    used_bytes: int
    bytes_capacity: int
    contention_drops: int
    evictions: int
    byte_truncations: int
    earliest_seq: int | None = None
    latest_seq: int | None = None


class WebPermitStatus(ResponseModel):
    """Serialized by `src/web/manager/status.rs`."""

    used: int
    available: int
    capacity: int
    closed: bool


class WebRuntimeStatus(ResponseModel):
    """Serialized by `src/web/manager/status.rs`."""

    runtime_instance: str
    generation_id: int
    limits: WebLimitsConfig
    manager: WebManagerStatus | None = None
    streams: WebStreamStatus | None = None
    budget: WebBudgetStatus | None = None
    websockets: WebSocketStatus | None = None
    learning: WebLearningStatus | None = None
    debug: WebDebugStatus | None = None
    permits: list[tuple[str, WebPermitStatus]]
    auxiliary_tasks: int
    session_incarnations_created: int
    session_incarnations_closed: int
    streams_opened: int
    streams_rejected: int
    bytes_up: int
    bytes_down: int
    limit_hits: int
    partial: list[str]


class WebStatusData(ResponseModel):
    """Serialized by `src/api/web_runtime.rs`."""

    lifecycle: str
    lifecycle_epoch: int
    lifecycle_age_ms: int
    available: bool
    reason: str | None = None
    listeners: list[str]
    effective_config_enabled: bool
    ingress: WebIngressStatus
    capacity: WebCapacityStatus
    decoy_upstream: WebDecoyUpstreamStatus
    decoy_fasttrack: WebDecoyFastTrackStatus
    carrier_negotiation: WebCarrierNegotiationStatus
    lifecycle_counters: WebLifecycleCountersStatus
    operator_lifecycle: OperatorLifecycleStatus | None = None
    runtime: WebRuntimeStatus | None = None


class WebSessionStatus(ResponseModel):
    """Serialized by `src/web/session/status.rs`."""

    trace_session_id: int
    client_ip: str
    host: str
    user: str
    key_id: str
    carrier: str
    attempt: int
    client_class: str
    automatic: bool
    state: str
    health_publication: str
    streams: int
    tasks: int
    lanes: int
    lane_open_waits: int
    websocket_lane_reservations: int
    websocket_active: bool
    pending_bytes: int
    pending_items: int
    control_bytes: int
    control_items: int
    age_ms: int
    idle_ms: int
    peer_idle_ms: int
    reconnect_grace_ms: int
    peer_deadline_remaining_ms: int
    negotiation_remaining_ms: int | None = None


class SessionRow(WebSessionStatus):
    """Serialized by `src/web/manager/status.rs`."""

    session_ref: str
    user_agent: str | None = None
    user_agent_id: str | None = None


class SessionPage(ResponseModel):
    """Serialized by `src/web/manager/status.rs`."""

    sessions: list[SessionRow]
    next_cursor: str | None = None
    scanned: int
    scan_truncated: bool
    partial_sessions: int
    partial: list[str]


class GoneSessionData(ResponseModel):
    """Serialized by `src/api/web_runtime.rs`."""

    session_ref: str
    state: str
    attempt: int
    carrier: str
    reason: str
    closed_age_ms: int


class ControlOperationStatus(ResponseModel):
    """Serialized by `src/web/manager/control.rs`."""

    operation_id: str
    state: str
    high_water_session_ref: str | None = None
    requested: int
    scanned: int
    matched: int
    close_signalled: int
    conflicted: int
    created_epoch_millis: int
    updated_epoch_millis: int
    failure: str | None = None


class DebugClearData(ResponseModel):
    """Serialized by `src/api/web_runtime.rs`."""

    runtime_instance: str
    records_cleared: int
    leased_bytes: int
    epoch: int


class LearningResetData(ResponseModel):
    """Serialized by `src/api/web_runtime.rs`."""

    runtime_instance: str
    entries_cleared: int
    epoch: int
