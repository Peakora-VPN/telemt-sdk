"""Telemt response contracts from API.md (66708d28); unknown fields are preserved."""

from pydantic import Field, JsonValue

from .base import ResponseModel
from .operations import ReloadAccepted


class ResetUserQuotaResponse(ResponseModel):
    username: str
    used_bytes: int
    last_reset_epoch_secs: int


class DeleteUserResponse(ResponseModel):
    username: str
    in_runtime: bool


class TlsDomainLink(ResponseModel):
    domain: str = Field(repr=False)
    link: str = Field(repr=False)


class UserLinks(ResponseModel):
    classic: list[str] = Field(repr=False)
    secure: list[str] = Field(repr=False)
    tls: list[str] = Field(repr=False)
    tls_domains: list[TlsDomainLink] = Field(repr=False)


class InheritedLimit(ResponseModel):
    """One effective limit with its configured override, global default, and origin."""

    value: int | None = None
    configured_override: int | None = None
    global_value: int
    origin: str


class UserLimitSnapshot(ResponseModel):
    """Per-user TCP and unique-IP limits sampled from one configuration snapshot."""

    max_tcp_conns: InheritedLimit
    max_unique_ips: InheritedLimit


class UserLimitState(ResponseModel):
    """Desired limit snapshot plus the sampled runtime-effective snapshot.

    ``effective`` is null when the user is absent from the sampled runtime or
    no runtime snapshot was supplied.
    """

    desired: UserLimitSnapshot
    effective: UserLimitSnapshot | None = None
    effective_scope: str
    subsystem_convergence: str


class SourceDenyState(ResponseModel):
    """Desired versus sampled-runtime source-deny state.

    ``effective`` and ``runtime_reload_required`` are null when no runtime
    snapshot is available; the lists differing means a generation reload is
    required for enforcement.
    """

    effective: list[str] | None = None
    runtime_reload_required: bool | None = None
    apply_mode: str
    reload_endpoint: str
    effective_scope: str


class UserInfo(ResponseModel):
    username: str
    enabled: bool
    in_runtime: bool
    user_ad_tag: str | None = None
    max_tcp_conns: int | None = None
    expiration_rfc3339: str | None = None
    data_quota_bytes: int | None = None
    quota_period: str | None = None
    rate_limit_up_bps: int | None = None
    rate_limit_down_bps: int | None = None
    max_unique_ips: int | None = None
    limits: UserLimitState
    source_deny: list[str]
    source_deny_status: SourceDenyState
    current_connections: int
    active_unique_ips: int
    active_unique_ips_list: list[str]
    recent_unique_ips: int
    recent_unique_ips_list: list[str]
    total_octets: int
    links: UserLinks = Field(repr=False)


class CreateUserResponse(ResponseModel):
    user: UserInfo
    secret: str = Field(repr=False)


class UserActiveIps(ResponseModel):
    username: str
    active_ips: list[str]


class DcEndpointWriters(ResponseModel):
    endpoint: str
    active_writers: int


class DcStatus(ResponseModel):
    dc: int
    endpoints: list[str]
    endpoint_writers: list[DcEndpointWriters]
    available_endpoints: int
    available_pct: float
    required_writers: int
    floor_min: int
    floor_target: int
    floor_max: int
    floor_capped: bool
    alive_writers: int
    coverage_pct: float
    fresh_alive_writers: int
    fresh_coverage_pct: float
    rtt_ms: float | None = None
    load: int


class DcStatusData(ResponseModel):
    middle_proxy_enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    dcs: list[DcStatus]


class MeWriterStatus(ResponseModel):
    writer_id: int
    dc: int | None = None
    endpoint: str
    generation: int
    state: str
    draining: bool
    degraded: bool
    bound_clients: int
    idle_for_secs: int | None = None
    rtt_ema_ms: float | None = None
    matches_active_generation: bool
    in_desired_map: bool
    allow_drain_fallback: bool
    drain_started_at_epoch_secs: int | None = None
    drain_deadline_epoch_secs: int | None = None
    drain_over_ttl: bool


class MeWritersSummary(ResponseModel):
    configured_dc_groups: int
    configured_endpoints: int
    available_endpoints: int
    available_pct: float
    required_writers: int
    alive_writers: int
    coverage_pct: float
    fresh_alive_writers: int
    fresh_coverage_pct: float


class MeWritersData(ResponseModel):
    middle_proxy_enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    summary: MeWritersSummary
    writers: list[MeWriterStatus]


class MinimalDcPathData(ResponseModel):
    dc: int
    ip_preference: str | None = None
    selected_addr_v4: str | None = None
    selected_addr_v6: str | None = None


class MinimalQuarantineData(ResponseModel):
    endpoint: str
    remaining_ms: int


class MinimalMeRuntimeData(ResponseModel):
    active_generation: int
    warm_generation: int
    warm_generations: list[int]
    pending_hardswap_generation: int
    pending_hardswap_age_secs: int | None = None
    reinit_inflight: int
    reinit_max_concurrency_effective: int
    hardswap_enabled: bool
    floor_mode: str
    adaptive_floor_idle_secs: int
    adaptive_floor_min_writers_single_endpoint: int
    adaptive_floor_min_writers_multi_endpoint: int
    adaptive_floor_recover_grace_secs: int
    adaptive_floor_writers_per_core_total: int
    adaptive_floor_cpu_cores_override: int
    adaptive_floor_max_extra_writers_single_per_core: int
    adaptive_floor_max_extra_writers_multi_per_core: int
    adaptive_floor_max_active_writers_per_core: int
    adaptive_floor_max_warm_writers_per_core: int
    adaptive_floor_max_active_writers_global: int
    adaptive_floor_max_warm_writers_global: int
    adaptive_floor_cpu_cores_detected: int
    adaptive_floor_cpu_cores_effective: int
    adaptive_floor_global_cap_raw: int
    adaptive_floor_global_cap_effective: int
    adaptive_floor_target_writers_total: int
    adaptive_floor_active_cap_configured: int
    adaptive_floor_active_cap_effective: int
    adaptive_floor_warm_cap_configured: int
    adaptive_floor_warm_cap_effective: int
    adaptive_floor_active_writers_current: int
    adaptive_floor_warm_writers_current: int
    me_keepalive_enabled: bool
    me_keepalive_interval_secs: int
    me_keepalive_jitter_secs: int
    me_keepalive_payload_random: bool
    rpc_proxy_req_every_secs: int
    me_reconnect_max_concurrent_per_dc: int
    me_reconnect_backoff_base_ms: int
    me_reconnect_backoff_cap_ms: int
    me_reconnect_fast_retry_count: int
    me_pool_drain_ttl_secs: int
    me_pool_force_close_secs: int
    me_pool_min_fresh_ratio: float
    me_bind_stale_mode: str
    me_bind_stale_ttl_secs: int
    me_single_endpoint_shadow_writers: int
    me_single_endpoint_outage_mode_enabled: bool
    me_single_endpoint_outage_disable_quarantine: bool
    me_single_endpoint_outage_backoff_min_ms: int
    me_single_endpoint_outage_backoff_max_ms: int
    me_single_endpoint_shadow_rotate_every_secs: int
    me_deterministic_writer_sort: bool
    me_writer_pick_mode: str
    me_writer_pick_sample_size: int
    me_socks_kdf_policy: str
    quarantined_endpoints_total: int
    quarantined_endpoints: list[MinimalQuarantineData]


class MinimalAllPayload(ResponseModel):
    me_writers: MeWritersData
    dcs: DcStatusData
    me_runtime: MinimalMeRuntimeData | None = None
    network_path: list[MinimalDcPathData]


class MinimalAllData(ResponseModel):
    enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    data: MinimalAllPayload | None = None


class ZeroDesyncData(ResponseModel):
    secure_padding_invalid_total: int
    desync_total: int
    desync_full_logged_total: int
    desync_suppressed_total: int
    desync_frames_bucket_0: int
    desync_frames_bucket_1_2: int
    desync_frames_bucket_3_10: int
    desync_frames_bucket_gt_10: int


class ZeroPoolData(ResponseModel):
    pool_swap_total: int
    pool_drain_active: int
    pool_force_close_total: int
    pool_stale_pick_total: int
    writer_removed_total: int
    writer_removed_unexpected_total: int
    refill_triggered_total: int
    refill_skipped_inflight_total: int
    refill_failed_total: int
    writer_restored_same_endpoint_total: int
    writer_restored_fallback_total: int


class ZeroCodeCount(ResponseModel):
    code: int
    total: int


class ZeroMiddleProxyData(ResponseModel):
    keepalive_sent_total: int
    keepalive_failed_total: int
    keepalive_pong_total: int
    keepalive_timeout_total: int
    rpc_proxy_req_signal_sent_total: int
    rpc_proxy_req_signal_failed_total: int
    rpc_proxy_req_signal_skipped_no_meta_total: int
    rpc_proxy_req_signal_response_total: int
    rpc_proxy_req_signal_close_sent_total: int
    reconnect_attempt_total: int
    reconnect_success_total: int
    handshake_reject_total: int
    handshake_error_codes: list[ZeroCodeCount]
    handshake_error_code_overflow_total: int
    reader_eof_total: int
    idle_close_by_peer_total: int
    route_drop_no_conn_total: int
    route_drop_channel_closed_total: int
    route_drop_queue_full_total: int
    route_drop_queue_full_base_total: int
    route_drop_queue_full_high_total: int
    d2c_batches_total: int
    d2c_batch_frames_total: int
    d2c_batch_bytes_total: int
    d2c_flush_reason_queue_drain_total: int
    d2c_flush_reason_batch_frames_total: int
    d2c_flush_reason_batch_bytes_total: int
    d2c_flush_reason_max_delay_total: int
    d2c_flush_reason_ack_immediate_total: int
    d2c_flush_reason_close_total: int
    d2c_data_frames_total: int
    d2c_ack_frames_total: int
    d2c_payload_bytes_total: int
    d2c_write_mode_coalesced_total: int
    d2c_write_mode_split_total: int
    d2c_quota_reject_pre_write_total: int
    d2c_quota_reject_post_write_total: int
    d2c_frame_buf_shrink_total: int
    d2c_frame_buf_shrink_bytes_total: int
    socks_kdf_strict_reject_total: int
    socks_kdf_compat_fallback_total: int
    endpoint_quarantine_total: int
    kdf_drift_total: int
    kdf_port_only_drift_total: int
    hardswap_pending_reuse_total: int
    hardswap_pending_ttl_expired_total: int
    single_endpoint_outage_enter_total: int
    single_endpoint_outage_exit_total: int
    single_endpoint_outage_reconnect_attempt_total: int
    single_endpoint_outage_reconnect_success_total: int
    single_endpoint_quarantine_bypass_total: int
    single_endpoint_shadow_rotate_total: int
    single_endpoint_shadow_rotate_skipped_quarantine_total: int
    floor_mode_switch_total: int
    floor_mode_switch_static_to_adaptive_total: int
    floor_mode_switch_adaptive_to_static_total: int


class UpstreamDcStatus(ResponseModel):
    dc: int
    latency_ema_ms: float | None = None
    ip_preference: str


class UpstreamStatus(ResponseModel):
    upstream_id: int
    route_kind: str
    address: str
    weight: int
    scopes: str
    healthy: bool
    fails: int
    last_check_age_secs: int
    effective_latency_ms: float | None = None
    dc: list[UpstreamDcStatus]


class UpstreamSummaryData(ResponseModel):
    configured_total: int
    healthy_total: int
    unhealthy_total: int
    direct_total: int
    socks4_total: int
    socks5_total: int
    shadowsocks_total: int


class ZeroUpstreamData(ResponseModel):
    connect_attempt_total: int
    connect_success_total: int
    connect_fail_total: int
    connect_failfast_hard_error_total: int
    connect_attempts_bucket_1: int
    connect_attempts_bucket_2: int
    connect_attempts_bucket_3_4: int
    connect_attempts_bucket_gt_4: int
    connect_duration_success_bucket_le_100ms: int
    connect_duration_success_bucket_101_500ms: int
    connect_duration_success_bucket_501_1000ms: int
    connect_duration_success_bucket_gt_1000ms: int
    connect_duration_fail_bucket_le_100ms: int
    connect_duration_fail_bucket_101_500ms: int
    connect_duration_fail_bucket_501_1000ms: int
    connect_duration_fail_bucket_gt_1000ms: int


class UpstreamsData(ResponseModel):
    enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    zero: ZeroUpstreamData
    summary: UpstreamSummaryData | None = None
    upstreams: list[UpstreamStatus] | None = None


class ClassCount(ResponseModel):
    class_: str = Field(alias="class")
    total: int


class ZeroCoreData(ResponseModel):
    uptime_seconds: float
    connections_total: int
    connections_bad_total: int
    connections_bad_by_class: list[ClassCount]
    handshake_failures_by_class: list[ClassCount]
    handshake_timeouts_total: int
    accept_permit_timeout_total: int
    configured_users: int
    telemetry_core_enabled: bool
    telemetry_user_enabled: bool
    telemetry_me_level: str
    conntrack_control_enabled: bool
    conntrack_control_available: bool
    conntrack_pressure_active: bool
    conntrack_event_queue_depth: int
    conntrack_rule_apply_ok: bool
    conntrack_rule_reconcile_success_total: int
    conntrack_rule_reconcile_error_total: int
    conntrack_rule_rollback_success_total: int
    conntrack_rule_rollback_error_total: int
    conntrack_delete_attempt_total: int
    conntrack_delete_success_total: int
    conntrack_delete_not_found_total: int
    conntrack_delete_error_total: int
    conntrack_close_event_drop_total: int


class ZeroAllData(ResponseModel):
    generated_at_epoch_secs: int
    core: ZeroCoreData
    upstream: ZeroUpstreamData
    middle_proxy: ZeroMiddleProxyData
    pool: ZeroPoolData
    desync: ZeroDesyncData


class RuntimeEdgeTlsFingerprintRow(ResponseModel):
    scope: str | None = None
    ja3: str
    ja3_raw: str
    ja4: str
    ja4_raw: str
    total: int
    auth_success: int
    bad_or_probe: int
    first_seen_epoch_secs: int
    last_seen_epoch_secs: int


class RuntimeEdgeTlsFingerprintsPayload(ResponseModel):
    limit: int
    retention_secs: int
    capacity: int
    dropped_total: int
    parse_error_total: int
    by_fingerprint: list[RuntimeEdgeTlsFingerprintRow]
    by_ip: list[RuntimeEdgeTlsFingerprintRow]
    by_cidr: list[RuntimeEdgeTlsFingerprintRow]
    by_user: list[RuntimeEdgeTlsFingerprintRow]


class RuntimeEdgeTlsFingerprintsData(ResponseModel):
    enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    data: RuntimeEdgeTlsFingerprintsPayload | None = None


class ApiEventRecord(ResponseModel):
    seq: int
    ts_epoch_secs: int
    event_type: str
    context: str


class RuntimeEdgeEventsPayload(ResponseModel):
    capacity: int
    dropped_total: int
    events: list[ApiEventRecord]


class RuntimeEdgeEventsData(ResponseModel):
    enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    data: RuntimeEdgeEventsPayload | None = None


class RuntimeEdgeConnectionTelemetryData(ResponseModel):
    user_enabled: bool
    throughput_is_cumulative: bool


class RuntimeEdgeConnectionUserData(ResponseModel):
    username: str
    current_connections: int
    total_octets: int


class RuntimeEdgeConnectionTopData(ResponseModel):
    limit: int
    by_connections: list[RuntimeEdgeConnectionUserData]
    by_throughput: list[RuntimeEdgeConnectionUserData]


class RuntimeEdgeConnectionTotalsData(ResponseModel):
    current_connections: int
    current_connections_me: int
    current_connections_direct: int
    active_users: int


class RuntimeEdgeConnectionCacheData(ResponseModel):
    ttl_ms: int
    served_from_cache: bool
    stale_cache_used: bool


class RuntimeEdgeConnectionsSummaryPayload(ResponseModel):
    cache: RuntimeEdgeConnectionCacheData
    totals: RuntimeEdgeConnectionTotalsData
    top: RuntimeEdgeConnectionTopData
    telemetry: RuntimeEdgeConnectionTelemetryData


class RuntimeEdgeConnectionsSummaryData(ResponseModel):
    enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    data: RuntimeEdgeConnectionsSummaryPayload | None = None


class RuntimeMeSelftestBndData(ResponseModel):
    addr_state: str
    port_state: str
    last_addr: str | None = None
    last_seen_age_secs: int | None = None


class RuntimeMeSelftestPidData(ResponseModel):
    pid: int
    state: str


class RuntimeMeSelftestIpFamilyData(ResponseModel):
    addr: str
    state: str


class RuntimeMeSelftestIpData(ResponseModel):
    v4: RuntimeMeSelftestIpFamilyData | None = None
    v6: RuntimeMeSelftestIpFamilyData | None = None


class RuntimeMeSelftestTimeskewData(ResponseModel):
    state: str
    max_skew_secs_15m: int | None = None
    samples_15m: int
    last_skew_secs: int | None = None
    last_source: str | None = None
    last_seen_age_secs: int | None = None


class RuntimeMeSelftestKdfData(ResponseModel):
    state: str
    ewma_errors_per_min: float
    threshold_errors_per_min: float
    errors_total: int


class RuntimeMeSelftestUpstreamData(ResponseModel):
    upstream_id: int
    route_kind: str
    address: str
    bnd: RuntimeMeSelftestBndData | None = None
    ip: str | None = None


class RuntimeMeSelftestPayload(ResponseModel):
    kdf: RuntimeMeSelftestKdfData
    timeskew: RuntimeMeSelftestTimeskewData
    ip: RuntimeMeSelftestIpData
    pid: RuntimeMeSelftestPidData
    bnd: RuntimeMeSelftestBndData | None = None
    upstreams: list[RuntimeMeSelftestUpstreamData] | None = None


class RuntimeMeSelftestData(ResponseModel):
    enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    data: RuntimeMeSelftestPayload | None = None


class RuntimeNatStunReflectionData(ResponseModel):
    addr: str
    age_secs: int


class RuntimeNatStunReflectionBlockData(ResponseModel):
    v4: RuntimeNatStunReflectionData | None = None
    v6: RuntimeNatStunReflectionData | None = None


class RuntimeNatStunServersData(ResponseModel):
    configured: list[str]
    live: list[str]
    live_total: int


class RuntimeNatStunFlagsData(ResponseModel):
    nat_probe_enabled: bool
    nat_probe_disabled_runtime: bool
    nat_probe_attempts: int


class RuntimeNatStunPayload(ResponseModel):
    flags: RuntimeNatStunFlagsData
    servers: RuntimeNatStunServersData
    reflection: RuntimeNatStunReflectionBlockData
    stun_backoff_remaining_ms: int | None = None


class RuntimeNatStunData(ResponseModel):
    enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    data: RuntimeNatStunPayload | None = None


class RuntimeUpstreamQualityDcData(ResponseModel):
    dc: int
    latency_ema_ms: float | None = None
    ip_preference: str


class RuntimeUpstreamQualityUpstreamData(ResponseModel):
    upstream_id: int
    route_kind: str
    address: str
    weight: int
    scopes: str
    healthy: bool
    fails: int
    last_check_age_secs: int
    effective_latency_ms: float | None = None
    dc: list[RuntimeUpstreamQualityDcData]


class RuntimeUpstreamQualitySummaryData(ResponseModel):
    configured_total: int
    healthy_total: int
    unhealthy_total: int
    direct_total: int
    socks4_total: int
    socks5_total: int
    shadowsocks_total: int


class RuntimeUpstreamQualityCountersData(ResponseModel):
    connect_attempt_total: int
    connect_success_total: int
    connect_fail_total: int
    connect_failfast_hard_error_total: int


class RuntimeUpstreamQualityPolicyData(ResponseModel):
    connect_retry_attempts: int
    connect_retry_backoff_ms: int
    connect_budget_ms: int
    unhealthy_fail_threshold: int
    connect_failfast_hard_errors: bool


class RuntimeUpstreamQualityData(ResponseModel):
    enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    policy: RuntimeUpstreamQualityPolicyData
    counters: RuntimeUpstreamQualityCountersData
    summary: RuntimeUpstreamQualitySummaryData | None = None
    upstreams: list[RuntimeUpstreamQualityUpstreamData] | None = None


class RuntimeMeQualityDcRttData(ResponseModel):
    dc: int
    rtt_ema_ms: float | None = None
    alive_writers: int
    required_writers: int
    coverage_pct: float


class RuntimeMeQualityDrainGateData(ResponseModel):
    route_quorum_ok: bool
    redundancy_ok: bool
    block_reason: str
    updated_at_epoch_secs: int


class RuntimeMeQualityFamilyStateData(ResponseModel):
    family: str
    state: str
    state_since_epoch_secs: int
    suppressed_until_epoch_secs: int | None = None
    fail_streak: int
    recover_success_streak: int


class RuntimeMeQualityRouteDropData(ResponseModel):
    no_conn_total: int
    channel_closed_total: int
    queue_full_total: int
    queue_full_base_total: int
    queue_full_high_total: int


class RuntimeMeQualityCountersData(ResponseModel):
    idle_close_by_peer_total: int
    reader_eof_total: int
    kdf_drift_total: int
    kdf_port_only_drift_total: int
    reconnect_attempt_total: int
    reconnect_success_total: int


class RuntimeMeQualityPayload(ResponseModel):
    counters: RuntimeMeQualityCountersData
    route_drops: RuntimeMeQualityRouteDropData
    family_states: list[RuntimeMeQualityFamilyStateData]
    drain_gate: RuntimeMeQualityDrainGateData
    dc_rtt: list[RuntimeMeQualityDcRttData]


class RuntimeMeQualityData(ResponseModel):
    enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    data: RuntimeMeQualityPayload | None = None


class RuntimeMePoolStateRefillDcData(ResponseModel):
    dc: int
    family: str
    inflight: int


class RuntimeMePoolStateRefillData(ResponseModel):
    inflight_endpoints_total: int
    inflight_dc_total: int
    running_dc_total: int
    pending_dc_total: int
    by_dc: list[RuntimeMePoolStateRefillDcData]


class RuntimeMePoolStateWriterHealthData(ResponseModel):
    healthy: int
    degraded: int
    draining: int


class RuntimeMePoolStateWriterContourData(ResponseModel):
    warm: int
    active: int
    draining: int


class RuntimeMePoolStateWriterData(ResponseModel):
    total: int
    alive_non_draining: int
    draining: int
    degraded: int
    contour: RuntimeMePoolStateWriterContourData
    health: RuntimeMePoolStateWriterHealthData


class RuntimeMePoolStateHardswapData(ResponseModel):
    enabled: bool
    pending: bool
    pending_writers_current: int
    pending_writer_deficit: int
    pending_missing_dc_groups: int
    pending_map_current: bool | None = None
    orphan_warm_writers_current: int
    replacement_preparing_current: int
    replacement_retiring_current: int


class RuntimeMePoolStateGenerationData(ResponseModel):
    active_generation: int
    warm_generation: int
    warm_generations: list[int]
    pending_hardswap_generation: int
    pending_hardswap_age_secs: int | None = None
    reinit_inflight: int
    reinit_max_concurrency_effective: int
    draining_generations: list[int]


class RuntimeMePoolStatePayload(ResponseModel):
    generations: RuntimeMePoolStateGenerationData
    hardswap: RuntimeMePoolStateHardswapData
    writers: RuntimeMePoolStateWriterData
    refill: RuntimeMePoolStateRefillData


class RuntimeMePoolStateData(ResponseModel):
    enabled: bool
    reason: str | None = None
    generated_at_epoch_secs: int
    data: RuntimeMePoolStatePayload | None = None


class SecurityWhitelistData(ResponseModel):
    generated_at_epoch_secs: int
    enabled: bool
    entries_total: int
    entries: list[str]


class SecurityPostureData(ResponseModel):
    api_read_only: bool
    api_whitelist_enabled: bool
    api_whitelist_entries: int
    api_auth_header_enabled: bool
    proxy_protocol_enabled: bool
    log_level: str
    telemetry_core_enabled: bool
    telemetry_user_enabled: bool
    telemetry_me_level: str


class EffectiveUserTcpPolicyLimits(ResponseModel):
    global_each: int


class EffectiveUserIpPolicyLimits(ResponseModel):
    global_each: int
    mode: str
    window_secs: int


class EffectiveMiddleProxyLimits(ResponseModel):
    floor_mode: str
    adaptive_floor_idle_secs: int
    adaptive_floor_min_writers_single_endpoint: int
    adaptive_floor_min_writers_multi_endpoint: int
    adaptive_floor_recover_grace_secs: int
    adaptive_floor_writers_per_core_total: int
    adaptive_floor_cpu_cores_override: int
    adaptive_floor_max_extra_writers_single_per_core: int
    adaptive_floor_max_extra_writers_multi_per_core: int
    adaptive_floor_max_active_writers_per_core: int
    adaptive_floor_max_warm_writers_per_core: int
    adaptive_floor_max_active_writers_global: int
    adaptive_floor_max_warm_writers_global: int
    reconnect_max_concurrent_per_dc: int
    reconnect_backoff_base_ms: int
    reconnect_backoff_cap_ms: int
    reconnect_fast_retry_count: int
    writer_pick_mode: str
    writer_pick_sample_size: int
    me2dc_fallback: bool
    me2dc_fast: bool


class EffectiveUpstreamLimits(ResponseModel):
    connect_retry_attempts: int
    connect_retry_backoff_ms: int
    connect_budget_ms: int
    unhealthy_fail_threshold: int
    connect_failfast_hard_errors: bool


class EffectiveTimeoutLimits(ResponseModel):
    client_handshake_secs: int
    client_first_byte_idle_secs: int
    tg_connect_secs: int
    client_keepalive_secs: int
    client_ack_secs: int
    me_one_retry: int
    me_one_timeout_ms: int


class EffectiveLimitsData(ResponseModel):
    update_every_secs: int
    me_reinit_every_secs: int
    me_pool_force_close_secs: int
    timeouts: EffectiveTimeoutLimits
    upstream: EffectiveUpstreamLimits
    middle_proxy: EffectiveMiddleProxyLimits
    user_ip_policy: EffectiveUserIpPolicyLimits
    user_tcp_policy: EffectiveUserTcpPolicyLimits


class RuntimeInitializationComponentData(ResponseModel):
    id: str
    title: str
    status: str
    started_at_epoch_ms: int | None = None
    finished_at_epoch_ms: int | None = None
    duration_ms: int | None = None
    attempts: int
    details: str | None = None


class RuntimeInitializationMeData(ResponseModel):
    status: str
    current_stage: str
    progress_pct: float
    init_attempt: int
    retry_limit: str
    last_error: str | None = None


class RuntimeInitializationData(ResponseModel):
    status: str
    degraded: bool
    current_stage: str
    progress_pct: float
    started_at_epoch_secs: int
    ready_at_epoch_secs: int | None = None
    total_elapsed_ms: int
    transport_mode: str
    me: RuntimeInitializationMeData
    components: list[RuntimeInitializationComponentData]


class RuntimeGatesData(ResponseModel):
    accepting_new_connections: bool
    conditional_cast_enabled: bool
    me_runtime_ready: bool
    me2dc_fallback_enabled: bool
    me2dc_fast_enabled: bool
    use_middle_proxy: bool
    route_mode: str
    reroute_active: bool
    reroute_to_direct_at_epoch_secs: int | None = None
    reroute_reason: str | None = None
    startup_status: str
    startup_stage: str
    startup_progress_pct: float


class SystemInfoData(ResponseModel):
    version: str
    target_arch: str
    target_os: str
    build_profile: str
    git_commit: str | None = None
    build_time_utc: str | None = None
    rustc_version: str | None = None
    process_started_at_epoch_secs: int
    uptime_seconds: float
    config_path: str
    config_hash: str
    config_reload_count: int
    last_config_reload_epoch_secs: int | None = None


class SummaryData(ResponseModel):
    uptime_seconds: float
    connections_total: int
    connections_bad_total: int
    connections_bad_by_class: list[ClassCount]
    handshake_failures_by_class: list[ClassCount]
    handshake_timeouts_total: int
    configured_users: int


class HealthReadyData(ResponseModel):
    ready: bool
    status: str
    reason: str | None = None
    admission_open: bool
    healthy_upstreams: int
    total_upstreams: int


class HealthData(ResponseModel):
    status: str
    read_only: bool


class NormalizationEffect(ResponseModel):
    """One value normalized while preparing a config patch, without values."""

    path: str
    code: str


class PatchConfigResponse(ResponseModel):
    revision: str
    restart_required: bool
    runtime_reload_required: bool
    process_restart_required: bool
    deferred_process_fields: list[str]
    changed: list[str]
    changed_paths: list[str]
    normalization_effects: list[NormalizationEffect]
    reload: ReloadAccepted | None = None


class ConfigData(ResponseModel):
    general: dict[str, JsonValue]
    timeouts: dict[str, JsonValue]
    censorship: dict[str, JsonValue]
    upstreams: list[dict[str, JsonValue]]
    dc_overrides: dict[str, JsonValue]
    web: dict[str, JsonValue]
    server: dict[str, JsonValue] | None = None
    network: dict[str, JsonValue] | None = None
