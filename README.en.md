<p align="center">
  <a href="https://github.com/Peakora-VPN/telemt-sdk/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Peakora-VPN/telemt-sdk/ci.yml?style=for-the-badge&amp;logo=githubactions&amp;logoColor=white&amp;label=CI" alt="CI status"></a>
  <a href="https://pypi.org/project/telemt-sdk/"><img src="https://img.shields.io/pypi/v/telemt-sdk?style=for-the-badge&amp;logo=pypi&amp;logoColor=white&amp;color=3776AB" alt="PyPI version"></a>
  <a href="#compatibility"><img src="https://img.shields.io/badge/Python-3.13%20%7C%203.14%20%7C%203.15-3776AB?style=for-the-badge&amp;logo=python&amp;logoColor=white" alt="Python 3.13, 3.14 and 3.15"></a>
  <a href="https://github.com/Peakora-VPN/telemt-sdk/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge" alt="MIT license"></a>
</p>
<p align="center">
  <a href="https://docs.astral.sh/uv/"><img src="https://img.shields.io/badge/managed%20with-uv-DE5FE9?style=flat-square&amp;logo=uv" alt="Managed with uv"></a>
  <a href="https://docs.astral.sh/ruff/"><img src="https://img.shields.io/badge/code%20style-Ruff-D7FF64?style=flat-square&amp;logo=ruff&amp;logoColor=black" alt="Code style: Ruff"></a>
  <a href="https://typing.python.org/"><img src="https://img.shields.io/badge/typing-PEP%20561-6366F1?style=flat-square" alt="Typed Python package"></a>
</p>

<p align="center"><a href="https://github.com/Peakora-VPN/telemt-sdk/blob/main/README.md">Русский</a> · <a href="https://github.com/Peakora-VPN/telemt-sdk/blob/main/README.en.md">English</a></p>

<h1 align="center">telemt-sdk</h1>
<p align="center">Async, typed Python access to the Telemt Control API.</p>
<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="https://github.com/Peakora-VPN/telemt-sdk/blob/main/docs/api-reference.md">API reference</a> ·
  <a href="https://github.com/Peakora-VPN/telemt-sdk/blob/main/CONTRIBUTING.md">Contributing</a> ·
  <a href="https://github.com/Peakora-VPN/telemt-sdk/issues">Issues</a>
</p>

Manage proxy users, quotas, configuration, runtime diagnostics and WEB sessions from Python.
`TelemtClient` groups operations into resource objects, reuses HTTP connections and returns
Pydantic models with concrete type annotations throughout nested responses.

- **54 API operations:** user management, health, statistics, configuration, access policy, capability discovery and WEB lifecycle control.
- **Async throughout:** use `async with`, `await` and concurrent reads with `asyncio.gather`.
- **Typed requests and responses:** input validation, editor completion and a `py.typed` marker.
- **Explicit concurrency control:** pass a response revision (`revision=`) and a runtime token (`runtime_match=`) to protect configuration and access-policy changes.
- **Predictable errors:** typed exceptions retain the HTTP status, Telemt error code, request ID and structured error details (`path`, `code`, `message`).

This is a client for Telemt's HTTP management API. MTProto transport and Telegram client
connections are handled by [Telemt](https://github.com/telemt/telemt).

## Installation

Requires Python **3.13, 3.14 or 3.15**. The distribution is named `telemt-sdk`; the import is `telemt`.

Install from [PyPI](https://pypi.org/project/telemt-sdk/):

```bash
uv add telemt-sdk
```

Or with pip:

```bash
python -m pip install telemt-sdk
```

For development setup, see [Contributing](https://github.com/Peakora-VPN/telemt-sdk/blob/main/CONTRIBUTING.md).

## Quick start

Enable the Control API in your Telemt configuration and set `TELEMT_AUTH_HEADER` to the
value of `server.api.auth_header`:

```python
import asyncio
import os

from telemt import TelemtClient


async def main() -> None:
    async with TelemtClient(
        "http://127.0.0.1:9091",
        auth_header=os.environ["TELEMT_AUTH_HEADER"],
    ) as client:
        health = await client.health.get()
        print(health.data.status)

        users = await client.users.list()
        for user in users.data:
            print(user.username, user.enabled, user.current_connections)


asyncio.run(main())
```

The SDK sends `auth_header` verbatim as `Authorization`. It does not prepend `Bearer`.
If your configured value is `Bearer ...`, pass that entire string. If authentication is
not configured on the server, omit the argument. Use the URL of your Control API listener,
not the MTProto or WEB ingress port.

By default, `server.api.whitelist` contains only `127.0.0.0/8`; an empty list allows
all addresses. To manage Telemt remotely, add your network's CIDR range to the Telemt
configuration file: the config API does not edit `whitelist` or `gray_action`. Checks
use the direct TCP peer's IP address; the `X-Forwarded-For` header is ignored.
Addresses outside the list follow `server.api.gray_action`: `drop` (the default) closes
the connection without an HTTP response, so the SDK raises `TransportError`; `api`
returns a structured `403 forbidden`, and `200` replies with an empty body that the SDK
rejects as `InvalidResponseError`.

The examples below run inside `async with TelemtClient(...) as client`
in an async function, as in the quick start.

## Client configuration

| Argument | Default | Meaning |
| --- | --- | --- |
| `base_url` | Required | Absolute HTTP(S) URL. `/v1` is appended if absent. Reverse proxy prefixes are preserved. |
| `auth_header` | `None` | Exact value of the server's `Authorization` header. |
| `timeout` | `30.0` | HTTPX timeout in seconds, or an `httpx.Timeout` object for separate connect/read/write/pool limits. |
| `http_client` | `None` | Optional `httpx.AsyncClient` for custom TLS, proxies, transports or connection limits. |
| `hooks` | `()` | `ClientHook` instances called around each request and response; see [HTTP hooks](#http-hooks). |

Both `https://proxy.example.com/control` and `https://proxy.example.com/control/v1`
target `/control/v1/...`. Credentials, query strings and fragments in `base_url` are rejected.

Use one client for multiple requests within an event loop:

```python
health, stats = await asyncio.gather(client.health.get(), client.stats.summary())
print(stats.data.connections_total)
```

Close connections with `async with` or `await client.aclose()`. A client cannot be reused
after closing. When you supply an HTTPX client, you own its lifetime:

```python
import httpx

async with httpx.AsyncClient(limits=httpx.Limits(max_connections=20)) as http:
    async with TelemtClient(
        "https://proxy.example.com",
        auth_header=os.environ["TELEMT_AUTH_HEADER"],
        timeout=httpx.Timeout(30.0, connect=5.0),
        http_client=http,
    ) as client:
        info = await client.system.info()
```

SDK parameters and explicit authorization take precedence
over HTTPX defaults. Redirects and automatic retries are disabled; a timed-out mutation
may already have reached the server.

### HTTP hooks

Pass `ClientHook` instances through `hooks` and override the callbacks you need:

```python
import httpx
from telemt import ClientHook, TelemtClient


class LoggingHook(ClientHook):
    async def on_request(self, request: httpx.Request) -> None:
        print(request.method, request.url.path)

    async def on_response(self, response: httpx.Response) -> None:
        print(response.status_code)


async with TelemtClient(
    "http://127.0.0.1:9091",
    auth_header=os.environ["TELEMT_AUTH_HEADER"],
    hooks=[LoggingHook()],
) as client:
    await client.health.get()
```

## Users and quotas

Create a user, adjust its limits, rotate the secret and manage its state:

```python
from telemt.models import CreateUserRequest, PatchUserRequest, RotateSecretRequest

created = await client.users.create(
    CreateUserRequest(
        username="alice",
        max_tcp_conns=10,
        data_quota_bytes=10_000_000_000,
        quota_period="monthly",
    )
)
# created.data.secret contains the generated secret; keep it out of logs.
print(created.data.user.username)

await client.users.update(
    "alice",
    PatchUserRequest(max_tcp_conns=20, expiration_rfc3339="2027-01-01T00:00:00Z"),
    revision=created.revision,
)

await client.users.rotate_secret("alice", RotateSecretRequest())
await client.users.reset_quota("alice")
await client.users.disable("alice")
await client.users.enable("alice")
# Delete explicitly when the account is no longer needed:
# await client.users.delete("alice")
```

Secrets and advertisement tags are 32 hexadecimal characters. Usernames contain 1–64
ASCII letters, digits, underscores, dots or hyphens. The names `.` and `..` are rejected
because HTTPX normalizes those path segments. Recurring quotas accept `daily`, `weekly`
or `monthly` and require a positive `data_quota_bytes` on creation.

The `source_deny` field accepts a list of IPv4 or IPv6 CIDR prefixes
(`"203.0.113.0/24"`). The list blocks the user's outbound connections from those
networks; changing it requires a runtime generation reload, reported through
`UserInfo.source_deny_status.runtime_reload_required`. On creation, an explicitly
passed `source_deny=None` serializes as JSON `null`, while an omitted field is not
sent at all.

### PATCH semantics

Omitted fields, `None` and zero have distinct meanings:

| Request | Effect |
| --- | --- |
| `PatchUserRequest()` | Leave existing settings unchanged. |
| `PatchUserRequest(max_tcp_conns=None)` | Remove the per-user override. |
| `PatchUserRequest(max_tcp_conns=0)` | Send an explicit zero; Telemt applies that setting's semantics. |
| `PatchUserRequest(enabled=False)` | Disable the user. |
| `PatchUserRequest(secret=None)` | Leave the secret unchanged, matching Telemt. |
| `PatchUserRequest(source_deny=["203.0.113.0/24"])` | Replace the list of denied networks. |
| `PatchUserRequest(source_deny=None)` | Clear the list of denied networks. |

Use `rotate_secret()` to generate a new secret. Request objects reject unknown fields and
invalid values. State-dependent checks, such as whether a user already exists, belong to
Telemt and produce API errors.

### Checking quota usage

`used_bytes` and `data_quota_bytes` are measured in bytes. For example, display usage
for users with monthly quotas in gigabytes:

```python
quotas = await client.stats.quota()
for quota in quotas.data.users:
    if quota.quota_period == "monthly":
        print(
            quota.username,
            f"{quota.used_bytes / 1_000_000_000:.2f} / "
            f"{quota.data_quota_bytes / 1_000_000_000:.2f} GB",
            quota.quota_next_reset_epoch_secs,
        )
```

## Responses and revisions

Every method returns `APIResponse[T]`:

| Field | Type | Meaning |
| --- | --- | --- |
| `data` | `T` | Typed operation result, such as `UserInfo` or `list[UserInfo]`. |
| `revision` | `str` | Server configuration revision for this response. |
| `status_code` | `int` | Actual HTTP response status. |
| `ok` | `Literal[True]` | A successfully decoded API envelope. |

Every method except `config.state()` returns `APIResponse[T]` with a required revision.
`config.state()` returns `NullableRevisionAPIResponse[ConfigStateData]`, whose `revision`
is `str | None`: the server omits the revision when the desired configuration is not yet
committed, so check for `None` before using it in `If-Match`.

Nested fields are models too: `user.links.tls_domains[0].domain` and
`status.runtime.manager.issuance_enabled` support type checking after nullable fields are
narrowed. Import models from `telemt.models`.

```python
current = await client.users.get("alice")
await client.users.update(
    "alice",
    PatchUserRequest(max_tcp_conns=30),
    revision=current.revision,
)
```

`revision=` becomes `If-Match`. A stale revision raises `ConflictError`. Re-read the
current state and decide whether your change is still valid before retrying. The client
does not store or automatically reuse a global revision, so concurrent responses remain
independent. WEB operations use `runtime_instance` instead.

Configuration and access-policy mutations additionally accept `runtime_match=`: an
opaque runtime-publication token from `config.state()` (`runtime.runtime_match`) or
from `ConfigValidationData.runtime`, sent as the `If-Runtime-Match` header. The SDK
validates the token before sending: 1–128 characters, hexadecimal digits and colons
only. A stale token raises `ConflictError` (409 `runtime_conflict`). The server applied
a different configuration before your write landed.

Response models retain unknown server fields in `model_extra`. Use
`model_dump(mode="json", by_alias=True)` for a JSON-compatible representation. Configuration
sections remain `dict[str, JsonValue]` because their contents are open configuration data;
known telemetry and WEB structures have explicit models.

## Configuration and reloads

Apply a patch and wait for the reload to finish:

```python
import asyncio

from telemt.models import PatchConfigRequest, ReloadRequest

current = await client.config.get()
changed = await client.config.update(
    PatchConfigRequest(censorship={"tls_domain": "front.example.com"}),
    revision=current.revision,
    reload=ReloadRequest(mode="drain", timeout_secs=30, failure_policy="rollback"),
)
if changed.data.reload is not None:
    progress = await client.system.wait_reload(
        changed.data.reload.reload_id, timeout=60, poll_interval=1
    )
    print(progress.data.state)
    for warning in progress.data.warnings:
        print(warning)
    if progress.data.deferred_process_fields:
        print("Restart required:", progress.data.deferred_process_fields)
    if progress.data.state != "succeeded":
        raise RuntimeError(progress.data.error or progress.data.state)
```

Editable sections are `general`, `timeouts`, `censorship`, `upstreams`, `dc_overrides`,
`web`, `server.listeners`, the five observable `server.api` settings
(`minimal_runtime_enabled`, `minimal_runtime_cache_ttl_ms`, `runtime_edge_enabled`,
`runtime_edge_cache_ttl_ms`, `runtime_edge_top_n`) and `network.dns_overrides`
(an empty list clears the DNS overrides). Other `server` and `network` keys are rejected
by the request model. Server-side validation determines which nested settings
can change and which require a process restart.

An HTTP `202` means accepted, not completed. Poll `system.reload_status(id)` with an
application-defined interval and deadline until `succeeded`, `rolled_back` or `failed`.
Read `warnings`, `deferred_process_fields` and `error` from the result. To trigger a
separate reload, call `system.reload(ReloadRequest(...))`. Drain mode requires a
`timeout_secs` value from 1 to 3600; instant mode does not accept it.

The server applies changes asynchronously: a watcher publishes the new configuration,
and a generation reload propagates it to running workers. The `restart_required`,
`runtime_reload_required` and `process_restart_required` flags on the `config.update()`
response and on `ConfigValidationData.apply` show which boundaries a patch must cross.
Do not restart the process while the flags are set or before `config.state()` reports
`comparison.status == "published_match"`.

### Configuration schema, state and preflight

Read the schema, compare desired and effective state, and preflight a patch:

```python
schema = await client.config.schema()
print(schema.data.schema_version, len(schema.data.fields))

state = await client.config.state()  # or client.config.state(["network", "access"])
print(state.revision, state.data.desired_status, state.data.comparison.status)

if state.revision is None:
    raise RuntimeError("configuration revision is not committed yet")
report = await client.config.validate(
    PatchConfigRequest(network={"dns_overrides": ["1.1.1.1"]}),
    revision=state.revision,
)
print(report.data.valid, report.data.changed_paths, report.data.touched_sections)
```

`config.schema()` returns configuration-field metadata: paths, defaults, constraints,
the apply policy (watcher, reload, effect) and the related API routes.

`config.state()` compares the desired and effective configuration: field projections,
watcher differences, reload observations and runtime. The `sections` parameter filters
sections and takes a non-empty sequence of unique names from `general`, `network`,
`server`, `timeouts`, `censorship`, `upstreams`, `dc_overrides`, `web`, `access`,
`logging` and `root`. Only `sections=None` omits the query parameter entirely; an empty
sequence, duplicates and unknown names raise `ValueError` before anything is sent.

`config.validate()` preflights a patch without persisting it: nothing is committed or
reserved, so it is safe to repeat. The result carries `valid`, `base_revision`,
`candidate_revision`, `changed_paths`, `normalization_effects`, `touched_sections` and
`apply` with the reload flags. On rejection the server returns structured error details
(see [Errors](#errors)).

### Access policy

Read the current policy, then apply a sparse patch:

```python
from telemt.models import AccessPolicyPatch, CidrRateLimitInput

policy = await client.access.get()
print(policy.data.desired, policy.data.published_match)

updated = await client.access.update(
    AccessPolicyPatch(
        user_max_tcp_conns_global_each=64,
        cidr_rate_limits={"203.0.113.0/24": CidrRateLimitInput(up_bps=10_000_000)},
    ),
    revision=policy.revision,
    runtime_match=policy.data.runtime.runtime_match,
)
print(updated.data.changed_paths)
```

`AccessPolicyPatch` is a sparse merge patch over the five policy fields: omitted fields
stay unchanged, an explicit `None` on a scalar restores the type default, an explicit
`None` on a `cidr_rate_limits` entry deletes that network's rule, and `None` for the
whole map clears every rule. A completely empty patch is rejected. `cidr_rate_limits`
keys accept CIDR prefixes and `*4/N`, `*6/N`, `*/N` templates; each value requires at
least one positive direction (`up_bps` or `down_bps`, up to 100 Gbit/s; zero means
"unlimited"). The response carries desired and effective snapshots, publication status
and `changed_paths` (PATCH only).

## WEB sessions and lifecycle

List a user's sessions and close them on the current runtime instance:

```python
from telemt.models import CloseRequest, RefsSelector, SessionQuery

status = await client.runtime.web.status()
if status.data.runtime is not None:
    page = await client.runtime.web.sessions(SessionQuery(user="alice", limit=50))
    if page.data.sessions:
        accepted = await client.runtime.web.close_sessions(
            CloseRequest(
                runtime_instance=status.data.runtime.runtime_instance,
                selector=RefsSelector(session_refs=[row.session_ref for row in page.data.sessions]),
            )
        )
        progress = await client.runtime.web.wait_operation(accepted.data.operation_id, timeout=60)
        print(progress.data.state)
```

To list every page of sessions for a user:

```python
from telemt.models import SessionQuery

async for session in client.runtime.web.iter_sessions(SessionQuery(user="alice", limit=100)):
    print(session.session_ref)
```

Session pages contain up to 200 rows. Pass `SessionQuery(cursor=page.data.next_cursor, ...)`
with the same filters for the next page, stopping when `next_cursor` is `None`.
`scan_truncated`, `partial_sessions` and `partial` describe snapshot limitations.

Use `RuntimeInstanceRequest` with `pause`, `resume`, `clear_debug` and
`reset_carrier_learning`; use `DrainRequest` with `drain`. `FilterSelector` selects
matching sessions. `AllSelector` requires `runtime.manager.issuance_enabled` to be false;
operator `pause()` changes a separate admission fence. Check the reported runtime state
before selecting all sessions. Use `drain()` for an operator-controlled shutdown of current work.
Session and operation references are scoped to the current server process.
Poll the returned operation ID to observe completion; acceptance alone is not completion.
`wait_operation()` treats `completed`, `failed` and `cancelled` as terminal states.

## Errors

Catch typed exceptions and inspect their details:

```python
from telemt import APIError, ConflictError, TransportError

try:
    current = await client.users.get("alice")
    disabled = await client.users.disable("alice", revision=current.revision)
except ConflictError as error:
    print("Conflict:", error.code, error.request_id)
except APIError as error:
    print(error.status_code, error.code, error.message)
except TransportError:
    # Read back server state before deciding whether to repeat a mutation.
    raise
```

| Exception | Meaning |
| --- | --- |
| `AuthenticationError` | HTTP 401. |
| `PermissionDeniedError` | HTTP 403, including read-only mode. |
| `NotFoundError` | HTTP 404. |
| `ConflictError` | HTTP 409, including revision conflicts and a stale runtime token. |
| `APIError` | Other server errors; includes `status_code`, `code`, `message`, `request_id` and `details`. |
| `RequestTimeoutError` | HTTPX timeout; a subclass of `TransportError`. |
| `TransportError` | Network/transport failure; the original exception is in `__cause__`. |
| `InvalidResponseError` | Invalid JSON, envelope or response schema. |

All SDK exceptions inherit from `TelemtError`. Request models reject invalid fields
with `pydantic.ValidationError`; SDK route-argument checks (`base_url`, `username`,
`sections`, `runtime_match`) raise a bare `ValueError`. Since `pydantic.ValidationError`
is a subclass of `ValueError`, `except ValueError` catches both. Task cancellation
propagates normally.

For rejected requests the server may attach structured details: `APIError.details`
holds a tuple of `FieldIssue` objects with `path`, `code` and `message` fields (for
example, `code="unknown_field"` naming the offending path on a configuration preflight).
The tuple is empty when the server provides no details.

Two status codes carry valid data: `health.ready()` returns readiness data on HTTP 503,
and `runtime.web.session()` returns `GoneSessionData` on HTTP 410. An error envelope on
either route still raises an exception. Use `isinstance(result.data, GoneSessionData)`
to distinguish an expired session from `SessionRow`.

## Compatibility

The SDK follows the [Telemt project](https://github.com/telemt/telemt) and its
[Control API](https://github.com/telemt/telemt/blob/main/docs/Architecture/API/API.md).
It covers all 54 Control API operations of Telemt **3.5.17** (verified against tag
`3.5.17`, commit
[`66708d2866f3f3a4541c4fa67984d408e71a8af4`](https://github.com/telemt/telemt/tree/66708d2866f3f3a4541c4fa67984d408e71a8af4))
and targets Telemt 3.5.17 and compatible 3.5.x releases. HTML `/web-status` and WEB
transport endpoints are outside this management client.

Supports Python 3.13, 3.14 and 3.15 on Linux and Windows. Optional Telemt
runtime features may return disabled/unavailable payloads: inspect `enabled`, `reason`,
`data` and `partial` where present. Preserving new response fields helps with additive
server changes; compatibility with every earlier or future Telemt version is not implied.

See the [complete method reference](https://github.com/Peakora-VPN/telemt-sdk/blob/main/docs/api-reference.md)
for resource names, request types and response types.

## Contributing and support

Bug reports and pull requests are welcome. Include your Python, SDK and Telemt versions,
a minimal example and the exception type or Telemt error code in an
[issue](https://github.com/Peakora-VPN/telemt-sdk/issues). Remove authorization headers,
secrets and private configuration from reports.

See [CONTRIBUTING.md](https://github.com/Peakora-VPN/telemt-sdk/blob/main/CONTRIBUTING.md)
for the uv development setup, linting, type checks and tests.

<p align="center"><strong>🤝 Project sponsor — Peakora VPN</strong></p>
<p align="center">
  <a href="https://peakora.network/">
    <img src="https://peakora.network/social-preview.png" width="600" alt="Peakora VPN — internet at your own pace">
  </a>
</p>
<p align="center">
  Secure access to the internet and AI services, with setup through Telegram.<br>
  <a href="https://peakora.network/">Discover Peakora →</a>
</p>

## License

[MIT](https://github.com/Peakora-VPN/telemt-sdk/blob/main/LICENSE) © 2026 Peakora-VPN.
