# Testing against Telemt

The default `uv run pytest` command needs no server or network access. It includes:

- `MockTransport` tests for requests, authentication, errors, timeouts and client ownership
- Replay of real successful responses for all 54 SDK operations, including live and gone
  WEB sessions and asynchronous operation states
- Field names, nested types and omitted-field checks against a source-derived inventory
- Request boundary cases and regression tests for behavior not fully described by API docs

The source inventory and recorded responses in `tests/fixtures` were checked against
Telemt **3.5.17**, commit
[`66708d2866f3f3a4541c4fa67984d408e71a8af4`](https://github.com/telemt/telemt/tree/66708d2866f3f3a4541c4fa67984d408e71a8af4).

`source-contracts.json` records serialized model shapes and fields, including
flattened Rust structs, serde aliases, nullable fields and `skip_serializing_if` behavior.
`live-responses.json` contains responses from the isolated configuration below. Secrets in
these fixtures belong only to disposable test users. No production credentials are used.

## Live integration test

`tests/integration/test_live.py` mutates users, quotas, configuration and WEB lifecycle.
Run it only against a disposable instance using `tests/integration/telemt.toml`.
It checks the expected initial test user before making changes. Do not point it at a
production server. The test is skipped unless both `TELEMT_TEST_URL` and
`TELEMT_TEST_WEB_URL` are set.
The scenario also covers discovery capabilities, the configuration schema, full and
section-filtered config state, preflight validation with structured invalid-field
details, preconditions sent as the `If-Match` and `If-Runtime-Match` headers,
access-policy update/restore, user `source_deny` create/patch/null with generation
reloads, `network.dns_overrides` update/clear, and API observability editing with
reload.

The following Bash script starts an isolated Linux x86-64 Telemt binary with Docker.
It uses temporary files and randomly assigned localhost ports. Prerequisites: Bash,
Docker, `curl`, `sha256sum`, `tar` and `uv`. Run from the repository root:

```bash
set -euo pipefail
audit_dir=$(mktemp -d)
audit_container="telemt-sdk-test-$(date +%s)-$$"
trap 'docker rm -f "$audit_container" >/dev/null 2>&1 || true' EXIT

curl -fL https://github.com/telemt/telemt/releases/download/3.5.17/telemt-x86_64-linux-musl.tar.gz \
  -o "$audit_dir/telemt.tar.gz"
echo "f1591635849e0aad31f147692b21726da2f49499aae3ece79f8760c92925133a  $audit_dir/telemt.tar.gz" \
  | sha256sum --check
tar -xzf "$audit_dir/telemt.tar.gz" -C "$audit_dir"
chmod +x "$audit_dir/telemt"
cp tests/integration/telemt.toml "$audit_dir/config.toml"

docker run -d --name "$audit_container" \
  -p 127.0.0.1::9091 -p 127.0.0.1::18080 \
  --mount "type=bind,source=$audit_dir,target=/audit" -w /audit \
  alpine:3 /audit/telemt /audit/config.toml

export TELEMT_TEST_URL="http://$(docker port "$audit_container" 9091/tcp)"
export TELEMT_TEST_WEB_URL="http://$(docker port "$audit_container" 18080/tcp)"
for attempt in $(seq 1 60); do
  curl -fsS -H 'Authorization: sdk-audit-test-auth' \
    "$TELEMT_TEST_URL/v1/health" >/dev/null && break
  sleep 1
done
uv run pytest tests/integration -v
```

On Windows, run the script as-is in Git Bash, which ships Bash, `curl`, `sha256sum`
and `tar`. From PowerShell, keep the same image, mount and port mapping, verify the
download with `Get-FileHash -Algorithm SHA256` against the checksum above instead of
`sha256sum --check`. Then set `$env:TELEMT_TEST_URL` and `$env:TELEMT_TEST_WEB_URL`
to the published localhost addresses. The configuration disables middle-proxy mode
and STUN; active Telegram traffic, middle-end (ME) writer behavior under load and
external network failover are outside this integration scenario.

## Updating recorded responses

On a fresh disposable instance, set the `TELEMT_TEST_RECORD` environment variable to
`tests/fixtures/live-responses.json` before running the live test. It records successful
responses only, retaining distinct status/state combinations. Review the result for
credentials and private addresses before committing, update the provenance above, then run
the complete offline suite on all three supported Python versions.

The source inventory is deliberately pinned. To update it, inspect Rust serialization
types reachable from the Control API, apply `serde(rename)`, flatten nested structs and
map `Option`, collections and primitive types to their Python equivalents. The source
path and Rust type are retained alongside each expected field for review. An upstream
addition must be reflected in SDK models, exports and the API reference as appropriate.
