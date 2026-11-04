# Testing against Telemt

The default `uv run pytest` command needs no server or network access. It includes:

- MockTransport tests for requests, authentication, errors, timeouts and client ownership.
- Replay of real successful responses for all 48 SDK operations, including live and gone
  WEB sessions and asynchronous operation states.
- Field names, nested types and omitted-field checks against a source-derived inventory.
- Request boundary cases and regression tests for behavior not fully described by API docs.

The source inventory and recorded responses in `tests/fixtures` were checked against
Telemt **3.5.16**, commit
[`84e5b827a6619fb2e09ad3d09f253cdffe04bc2f`](https://github.com/telemt/telemt/tree/84e5b827a6619fb2e09ad3d09f253cdffe04bc2f).
This is fixture provenance, not a claim that all server configurations or versions were tested.

`source-contracts.json` records 138 serialized model shapes and 1001 fields, including
flattened Rust structs, serde aliases, nullable fields and `skip_serializing_if` behavior.
`live-responses.json` contains responses from the isolated configuration below. Secrets in
these fixtures belong only to disposable test users. No production credentials are used.

## Live integration test

`tests/integration/test_live.py` mutates users, quotas, configuration and WEB lifecycle.
Run it only against a disposable instance using `tests/integration/telemt.toml`.
It checks the expected initial test user before making changes. Do not point it at a
production server. The test is skipped unless both test URL environment variables are set.

The following Bash commands start an isolated Linux x86-64 Telemt binary with Docker.
They use temporary files and randomly assigned localhost ports. Docker and `curl` must
already be available. Run from the repository root:

```bash
set -euo pipefail
audit_dir=$(mktemp -d)
audit_container="telemt-sdk-test-$(date +%s)-$$"
trap 'docker rm -f "$audit_container" >/dev/null 2>&1 || true' EXIT

curl -fL https://github.com/telemt/telemt/releases/download/3.5.16/telemt-x86_64-linux-musl.tar.gz \
  -o "$audit_dir/telemt.tar.gz"
echo "05d7c32eff5990285657408cf383614d845ecc06aac0d5adc02a86d72c907146  $audit_dir/telemt.tar.gz" \
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

On Windows, use the same image, mount and environment variables from PowerShell; set
`$env:TELEMT_TEST_URL` and `$env:TELEMT_TEST_WEB_URL` to the published localhost addresses.
Remove only the container created for this test when finished. The configuration disables
middle-proxy mode and STUN; active Telegram traffic, ME writer behavior under load and
external network failover are outside this integration scenario.

## Updating recorded responses

On a fresh disposable instance, set `TELEMT_TEST_RECORD` to
`tests/fixtures/live-responses.json` before running the live test. It records successful
responses only, retaining distinct status/state combinations. Review the result for
credentials and private addresses before committing, update the provenance above, then run
the complete offline suite on all three supported Python versions.

The source inventory is deliberately pinned. To update it, inspect Rust serialization
types reachable from the Control API, apply `serde(rename)`, flatten nested structs and
map `Option`, collections and primitive types to their Python equivalents. The source
path and Rust type are retained alongside each expected field for review. An upstream
addition must be reflected in SDK models, exports and the API reference as appropriate.
