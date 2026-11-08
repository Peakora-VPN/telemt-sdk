# Contributing

For a bug report, include a minimal reproduction,
the Python/SDK/Telemt versions and the relevant API error code. Remove secrets and
private configuration before opening an issue.

## Development setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
git clone https://github.com/Peakora-VPN/telemt-sdk.git
cd telemt-sdk
uv python install 3.13 3.14 3.15
uv sync --locked
```

Dependencies belong in `pyproject.toml`; commit `uv.lock` when changing them.

## Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=telemt --cov-report=term-missing
uv run --isolated --python 3.13 pytest
uv run --isolated --python 3.15 pytest
uv build
```

Run `uv run ruff format .` to apply formatting. Mypy uses strict mode for the SDK,
release verification script and consumer examples in `tests/typing`.

The default test suite is offline. It checks transport/error behavior, request validation,
all resource routes, recorded real-server responses and response contracts extracted from
Telemt's Rust types. Optional tests against a disposable server are described in
[Testing against Telemt](docs/testing.md).

CI runs on pull requests and release tags (`v*`), including new commits to open pull requests.
It runs Ruff and mypy, then tests on Python 3.13, 3.14 and 3.15 under Linux and Windows, and builds
the wheel and source distribution.

## Changing the API

Check both Telemt's API documentation and its handlers/serialization types. Update the
request or response model, the resource method, public exports, tests and the method
reference together. Preserve the difference between an omitted PATCH field and explicit
JSON `null`. Keep configuration revisions attached to individual responses.

When updating compatibility fixtures, record the upstream commit and how the responses
were obtained. Add a regression test for behavioral fixes. Include a consumer type assertion when
changing a public return type.

## Pull requests

Explain the observed problem, the new behavior and the checks you ran. Note any API change
that requires callers to update. Contributions are provided under the repository's
[MIT license](LICENSE).

Use `feat:`, `fix:` or `perf:` commit titles for SDK changes. Mark incompatible changes
with `!` or a `BREAKING CHANGE:` footer. These messages appear in release highlights.
