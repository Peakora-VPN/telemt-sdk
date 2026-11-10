# API reference

All resource methods are asynchronous. Each returns `APIResponse[T]`; the tables name `T`.
Paths below are relative to `/v1`. Import request and response models from `telemt.models`.

The client covers all 54 Control API operations of Telemt 3.5.17 (source tag `3.5.17`,
commit `66708d2866f3f3a4541c4fa67984d408e71a8af4`). `config.state()` is the one method
returning `NullableRevisionAPIResponse[T]`, whose `revision` is `str | None`.

See the [README](../README.md) for authentication, lifecycle, revisions and error handling.

## `client.health`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `get()` | `GET health` | `HealthData` |
| `ready()` | `GET health/ready` | `HealthReadyData` |

## `client.system`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `reload(request=None, *, revision=None)` | `POST system/reload` | `ReloadAccepted` |
| `reload_status(reload_id)` | `GET system/reload/{reload_id}` | `ReloadStatus` |
| `info()` | `GET system/info` | `SystemInfoData` |

## `client.users`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `get(username)` | `GET users/{username}` | `UserInfo` |
| `create(request, *, revision=None)` | `POST users` | `CreateUserResponse` |
| `update(username, patch, *, revision=None)` | `PATCH users/{username}` | `UserInfo` |
| `delete(username, *, revision=None)` | `DELETE users/{username}` | `DeleteUserResponse` |
| `rotate_secret(username, request=None, *, revision=None)` | `POST users/{username}/rotate-secret` | `CreateUserResponse` |
| `enable(username, *, revision=None)` | `POST users/{username}/enable` | `UserInfo` |
| `disable(username, *, revision=None)` | `POST users/{username}/disable` | `UserInfo` |
| `reset_quota(username, *, revision=None)` | `POST users/{username}/reset-quota` | `ResetUserQuotaResponse` |
| `list()` | `GET users` | `list[UserInfo]` |

## `client.config`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `update(patch, *, revision=None, runtime_match=None, reload=None)` | `PATCH config` | `PatchConfigResponse` |
| `get()` | `GET config` | `ConfigData` |
| `schema()` | `GET config/schema` | `ConfigSchemaData` |
| `state(sections=None)` | `GET config/state` | `ConfigStateData` (nullable revision) |
| `validate(patch, *, revision=None, runtime_match=None, reload=None)` | `POST config/validate` | `ConfigValidationData` |

`state(sections=None)` returns `NullableRevisionAPIResponse[ConfigStateData]`; the
server omits `revision` until the desired configuration is committed. `sections` takes
a non-empty sequence of unique names from `general`, `network`, `server`, `timeouts`,
`censorship`, `upstreams`, `dc_overrides`, `web`, `access`, `logging` and `root`,
sent as one comma-separated query value; only `None` omits the query. Empty sequences,
duplicates and unknown names raise `ValueError`.

`validate()` preflights a patch without persisting or reserving anything: the result
carries `valid`, `base_revision`, `candidate_revision`, `changed_paths`,
`normalization_effects`, `touched_sections`, `warnings` and `apply` (reload flags).
A rejected candidate raises `APIError` whose `details` list the offending paths.

## `client.discovery`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `capabilities()` | `GET capabilities` | `CapabilitiesData` |

`CapabilitiesData` exposes the implemented operation catalog (`OperationCapability`
rows with gate, availability and mutation policy), `api_version`, `schema_version`,
`software_version` and `read_only`. Operation catalogs remain server-provided data;
the SDK does not model them as constants.

## `client.access`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `get()` | `GET access/policy` | `AccessPolicyData` |
| `update(patch, *, revision=None, runtime_match=None)` | `PATCH access/policy` | `AccessPolicyData` |

Both methods return desired/effective policy snapshots, the runtime baseline
(`runtime.runtime_match` feeds `If-Runtime-Match`), publication status and
`changed_paths` (PATCH only; GET omits the field).

## `client.limits`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `effective()` | `GET limits/effective` | `EffectiveLimitsData` |

## `client.security`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `posture()` | `GET security/posture` | `SecurityPostureData` |
| `whitelist()` | `GET security/whitelist` | `SecurityWhitelistData` |

## `client.stats`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `summary()` | `GET stats/summary` | `SummaryData` |
| `zero_all()` | `GET stats/zero/all` | `ZeroAllData` |
| `upstreams()` | `GET stats/upstreams` | `UpstreamsData` |
| `minimal_all()` | `GET stats/minimal/all` | `MinimalAllData` |
| `me_writers()` | `GET stats/me-writers` | `MeWritersData` |
| `dcs()` | `GET stats/dcs` | `DcStatusData` |
| `users()` | `GET stats/users` | `list[UserInfo]` |
| `active_ips()` | `GET stats/users/active-ips` | `list[UserActiveIps]` |
| `quota()` | `GET stats/users/quota` | `UserQuotaData` |

## `client.runtime`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `events_recent(*, limit=None)` | `GET runtime/events/recent` | `RuntimeEdgeEventsData` |
| `tls_fingerprints(*, limit=None)` | `GET runtime/tls-fingerprints` | `RuntimeEdgeTlsFingerprintsData` |
| `gates()` | `GET runtime/gates` | `RuntimeGatesData` |
| `initialization()` | `GET runtime/initialization` | `RuntimeInitializationData` |
| `me_pool_state()` | `GET runtime/me_pool_state` | `RuntimeMePoolStateData` |
| `me_quality()` | `GET runtime/me_quality` | `RuntimeMeQualityData` |
| `upstream_quality()` | `GET runtime/upstream_quality` | `RuntimeUpstreamQualityData` |
| `nat_stun()` | `GET runtime/nat_stun` | `RuntimeNatStunData` |
| `me_selftest()` | `GET runtime/me-selftest` | `RuntimeMeSelftestData` |
| `connections_summary()` | `GET runtime/connections/summary` | `RuntimeEdgeConnectionsSummaryData` |

## `client.runtime.web`

| Method | HTTP route | Response data |
| --- | --- | --- |
| `sessions(query=None)` | `GET runtime/web/sessions` | `SessionPage` |
| `session(session_ref)` | `GET runtime/web/sessions/{session_ref}` | `GoneSessionData \| SessionRow` |
| `close_sessions(request)` | `POST runtime/web/sessions/close` | `ControlOperationStatus` |
| `operation(operation_id)` | `GET runtime/web/operations/{operation_id}` | `ControlOperationStatus` |
| `clear_debug(request)` | `POST runtime/web/debug/clear` | `DebugClearData` |
| `reset_carrier_learning(request)` | `POST runtime/web/carrier-learning/reset` | `LearningResetData` |
| `pause(request)` | `POST runtime/web/lifecycle/pause` | `OperatorLifecycleStatus` |
| `drain(request)` | `POST runtime/web/lifecycle/drain` | `OperatorLifecycleStatus` |
| `resume(request)` | `POST runtime/web/lifecycle/resume` | `OperatorLifecycleStatus` |
| `status()` | `GET runtime/web/status` | `WebStatusData` |

## Request models

| Model | Accepted fields / purpose |
| --- | --- |
| `CreateUserRequest` | Required `username`; optional `secret` and user settings below. Omitted secret is generated by Telemt. |
| `PatchUserRequest` | Optional `secret` and user settings. Omitted fields remain unchanged; `None` clears overrides, except `secret=None` which is a no-op. |
| `RotateSecretRequest` | Optional `secret`; omit to generate a new one. |
| `PatchConfigRequest` | At least one of `general`, `timeouts`, `censorship`, `upstreams`, `dc_overrides`, `web`, `server`, `network`. In `server` only `listeners` and `api` are editable, and `api` only accepts the five observability keys. In `network` only `dns_overrides` is editable (`[]` clears). |
| `AccessPolicyPatch` | Sparse merge patch over `user_max_tcp_conns_global_each`, `user_max_unique_ips_global_each`, `user_max_unique_ips_mode`, `user_max_unique_ips_window_secs` and `cidr_rate_limits`. Omitted fields stay unchanged; explicit scalar `None` restores the default; a `None` map entry deletes that rule; `None` for the map clears all rules. An empty patch is rejected. |
| `CidrRateLimitInput` | `up_bps` / `down_bps` from 0 to 100 Gbit/s; at least one direction must be positive (0 means unlimited). |
| `ReloadRequest` | `mode="instant"` or `"drain"`; `timeout_secs` required only for drain (1-3600); `failure_policy="keep_new"` or `"rollback"`. |
| `SessionQuery` | Session filters, optional `limit` (1-200) and `cursor`. An exact `session_ref` cannot be combined with pagination. |
| `RuntimeInstanceRequest` | Required `runtime_instance` from the current WEB status. |
| `DrainRequest` | Required `runtime_instance` and `timeout_secs` (1-3600). |
| `CloseRequest` | Required `runtime_instance` and a typed `selector`. |

User settings shared by creation and updates:

| Field | Type | Meaning |
| --- | --- | --- |
| `user_ad_tag` | `str \| None` | 32 hexadecimal characters. |
| `max_tcp_conns` | `int \| None` | Per-user connection override. |
| `expiration_rfc3339` | `str \| None` | RFC3339 timestamp; preserve the supplied timezone. |
| `data_quota_bytes` | `int \| None` | Traffic quota in bytes. |
| `quota_period` | `"daily" \| "weekly" \| "monthly" \| None` | Recurring reset period; requires positive quota on creation. |
| `rate_limit_up_bps` | `int \| None` | Upload rate in bits per second. |
| `rate_limit_down_bps` | `int \| None` | Download rate in bits per second. |
| `max_unique_ips` | `int \| None` | Per-user unique-IP override. |
| `enabled` | `bool \| None` | User enabled override. |
| `source_deny` | `list[str] \| None` | IPv4/IPv6 CIDR prefixes denied for this user's outbound connections. |

Integer limits are unsigned 64-bit values. Zero is sent as zero, not omitted; its meaning
is determined by Telemt for each setting. Sparse models (`CreateUserRequest`,
`PatchUserRequest`, `PatchConfigRequest`, `AccessPolicyPatch`) send an explicitly set
`None` as JSON `null` on both creation and PATCH, while omitted fields stay absent;
other request models omit `None` fields.

## WEB filters and selectors

`SessionQuery` and `FilterSelector` share these filters:

- `session_ref`: `ws1.<32 lowercase hex runtime instance>.<16 lowercase hex nonzero ID>`.
- `ip`: canonical IPv4 or IPv6; mapped IPv6 uses `::ffff:192.0.2.1` notation; no zone IDs.
- `host`: nonempty string, at most 253 UTF-8 bytes.
- `user`: nonempty string, at most 64 UTF-8 bytes.
- `user_agent_id`: 32 lowercase hexadecimal characters.
- `key_id`: 16 lowercase hexadecimal characters.
- `carrier`: `https`, `https-lanes`, `websocket` or `websocket-lanes`.
- `state`: `provisional`, `replacing`, `committed`, `healthy`, `closing`, `superseded` or `closed`.

`RefsSelector(session_refs=[...])` accepts 1-200 unique references.
`FilterSelector(...)` requires at least one filter. `AllSelector()` requires the server's
manager issuance to be disabled. All references in a close request must belong to its
`runtime_instance`. Operation IDs use the `wo1` prefix and are also process-scoped.

WEB operator drain IDs belong to `OperatorLifecycleStatus.drain`; observe them through
`runtime.web.status()`. `runtime.web.operation()` polls close-session operations.

## Response behavior

- Known fields are validated strictly. Optional runtime sections can be `None`.
- New server fields are retained in `model_extra`; `model_dump()` includes them.
- JSON names that collide with Python keywords use an alias: `ClassCount.class_` maps to `class`.
- WEB permits are `list[tuple[str, WebPermitStatus]]`; JSON arrays are decoded into typed pairs.
- Configuration sections use `dict[str, JsonValue]` and remain extensible.
- Server enum values in responses are strings to tolerate new variants. Request choices
  use `Literal` types and are validated before sending.
- Error envelopes nest structured `details` (each with `path`, `code`, `message`) inside
  `error`; `APIError.details` exposes them as a tuple of `FieldIssue`. The tuple is empty
  when the server omits details.
- Sparse bodies (`CreateUserRequest`, `PatchUserRequest`, `PatchConfigRequest`,
  `AccessPolicyPatch`) keep omitted fields absent and send explicit `None` values as
  JSON `null`; other request models omit `None` fields.
- `runtime_match` values are validated before transport: 1–128 characters, hexadecimal
  digits and colons only, sent as `If-Runtime-Match`. `revision` is sent as `If-Match`.
- `config.state()` returns `NullableRevisionAPIResponse[ConfigStateData]` with
  `revision: str | None`; every other method returns `APIResponse[T]` with `revision: str`.
- `health.ready()` can return valid readiness data with HTTP 503.
- `runtime.web.session()` returns `SessionRow` for a live session and `GoneSessionData`
  with HTTP 410 for a retained closed-session record.

Model definitions, including all nested fields, are in
[`responses.py`](../src/telemt/models/responses.py),
[`web.py`](../src/telemt/models/web.py),
[`operations.py`](../src/telemt/models/operations.py),
[`discovery.py`](../src/telemt/models/discovery.py),
[`config.py`](../src/telemt/models/config.py) and
[`access.py`](../src/telemt/models/access.py).

## Iteration and waiting

- `system.wait_reload(reload_id, *, timeout=60, poll_interval=1)` returns
  `APIResponse[ReloadStatus]` on `succeeded`, `rolled_back` or `failed`.
- `runtime.web.wait_operation(operation_id, *, timeout=60, poll_interval=1)` returns
  `APIResponse[ControlOperationStatus]` on `completed`, `failed` or `cancelled`.
- `runtime.web.iter_sessions(query=None)` yields `SessionRow` across pages, preserving
  filters and leaving the supplied query unchanged. Use `sessions()` when you need
  snapshot metadata such as `partial` and `scan_truncated`. A repeated cursor raises
  `ValueError`; iteration does not provide a consistent snapshot across requests.

Wait timeouts and polling intervals must be finite positive seconds. The overall deadline
includes HTTP requests and raises built-in `TimeoutError`. Cancellation and API errors
propagate. A failed operation is returned as data; inspect its state and error details.
These helpers only read status; they do not retry mutations or cancel server operations.

## Client hooks

Import `ClientHook` from `telemt`, override `async on_request(request: httpx.Request)`
and/or `async on_response(response: httpx.Response)`, and pass instances using
`TelemtClient(..., hooks=[hook])`. Both methods return `None` and default to no-ops.
The client copies the hook sequence at construction and calls hooks in order.
Request hooks run before HTTPX sends the request. Response hooks run after the body
has been read, before API decoding, including HTTP error responses.
No response callback runs on transport failure. Callback errors and cancellation propagate;
a request callback error prevents sending, while a response callback error occurs after
any server-side mutation. Instances may serve concurrent requests: store per-request state
in `request.extensions`, not shared instance attributes.
Existing HTTPX event hooks remain unchanged; SDK hooks apply only to this SDK client.
