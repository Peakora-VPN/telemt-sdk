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

- **48 API operations:** user management, health, statistics, reloads and WEB lifecycle control.
- **Async throughout:** use `async with`, `await` and concurrent reads with `asyncio.gather`.
- **Typed requests and responses:** input validation, editor completion and a `py.typed` marker.
- **Explicit concurrency control:** pass a response revision to protect configuration changes.
- **Predictable errors:** typed exceptions retain the HTTP status, Telemt error code and request ID.

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

For development setup, see [Contributing](CONTRIBUTING.md).

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

The examples below run inside `async with TelemtClient(...) as client`
in an async function, as in the quick start.

## Client configuration

| Argument | Default | Meaning |
| --- | --- | --- |
| `base_url` | Required | Absolute HTTP(S) URL. `/v1` is appended if absent. Reverse proxy prefixes are preserved. |
| `auth_header` | `None` | Exact value of the server's `Authorization` header. |
| `timeout` | `30.0` | HTTPX timeout in seconds, or an `httpx.Timeout` object for separate connect/read/write/pool limits. |
| `http_client` | `None` | Optional `httpx.AsyncClient` for custom TLS, proxies, transports or connection limits. |

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

## Users and quotas

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

updated = await client.users.update(
    "alice",
    PatchUserRequest(max_tcp_conns=20, expiration_rfc3339="2027-01-01T00:00:00Z"),
    revision=created.revision,
)

rotated = await client.users.rotate_secret("alice", RotateSecretRequest())
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

### PATCH semantics

Omitted fields, `None` and zero have distinct meanings:

| Request | Effect |
| --- | --- |
| `PatchUserRequest()` | Leave existing settings unchanged. |
| `PatchUserRequest(max_tcp_conns=None)` | Remove the per-user override. |
| `PatchUserRequest(max_tcp_conns=0)` | Send an explicit zero; Telemt applies that setting's semantics. |
| `PatchUserRequest(enabled=False)` | Disable the user. |
| `PatchUserRequest(secret=None)` | Leave the secret unchanged, matching Telemt. |

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

Response models retain unknown server fields in `model_extra`. Use
`model_dump(mode="json", by_alias=True)` for a JSON-compatible representation. Configuration
sections remain `dict[str, JsonValue]` because their contents are open configuration data;
known telemetry and WEB structures have explicit models.

## Configuration and reloads

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
    async with asyncio.timeout(60):
        while True:
            progress = await client.system.reload_status(changed.data.reload.reload_id)
            if progress.data.state in {"succeeded", "rolled_back", "failed"}:
                break
            await asyncio.sleep(1)

    print(progress.data.state)
    for warning in progress.data.warnings:
        print(warning)
    if progress.data.deferred_process_fields:
        print("Restart required:", progress.data.deferred_process_fields)
    if progress.data.state != "succeeded":
        raise RuntimeError(progress.data.error or progress.data.state)
```

Editable sections are `general`, `timeouts`, `censorship`, `upstreams`, `dc_overrides`,
`web` and `server.listeners`. Server-side validation determines which nested settings
can change and which require a process restart.

An HTTP `202` means accepted, not completed. Poll `system.reload_status(id)` with an
application-defined interval and deadline until `succeeded`, `rolled_back` or `failed`.
Read `warnings`, `deferred_process_fields` and `error` from the result. To trigger a
separate reload, call `system.reload(ReloadRequest(...))`. Drain mode requires a
`timeout_secs` value from 1 to 3600; instant mode does not accept it.

## WEB sessions and lifecycle

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
        progress = await client.runtime.web.operation(accepted.data.operation_id)
        print(progress.data.state)
```

To list every page of sessions for a user:

```python
from telemt.models import SessionQuery

cursor: str | None = None
while True:
    page = await client.runtime.web.sessions(
        SessionQuery(user="alice", limit=100, cursor=cursor)
    )
    for session in page.data.sessions:
        print(session.session_ref)
    cursor = page.data.next_cursor
    if cursor is None:
        break
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

## Errors

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
| `ConflictError` | HTTP 409, including revision conflicts. |
| `APIError` | Other server errors; includes `status_code`, `code`, `message`, `request_id`. |
| `RequestTimeoutError` | HTTPX timeout; a subclass of `TransportError`. |
| `TransportError` | Network/transport failure; the original exception is in `__cause__`. |
| `InvalidResponseError` | Invalid JSON, envelope or response schema. |

All SDK exceptions inherit from `TelemtError`. Invalid request models raise
`pydantic.ValidationError`; invalid route arguments raise `ValueError` (including its
`ValidationError` subclass). Task cancellation propagates normally.

Two status codes carry valid data: `health.ready()` returns readiness data on HTTP 503,
and `runtime.web.session()` returns `GoneSessionData` on HTTP 410. An error envelope on
either route still raises an exception. Use `isinstance(result.data, GoneSessionData)`
to distinguish an expired session from `SessionRow`.

## Compatibility

The SDK follows the [Telemt project](https://github.com/telemt/telemt) and its
[Control API](https://github.com/telemt/telemt/blob/main/docs/Architecture/API/API.md).
The SDK covers all 48 canonical Control API operations;
HTML `/web-status` and WEB transport endpoints are outside this management client.

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
