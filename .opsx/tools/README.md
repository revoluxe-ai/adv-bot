# OPSX central catalog tools

## Tool

`opsx-central-catalog.mjs` — Node ESM, no dependencies.

```bash
node .opsx/tools/opsx-central-catalog.mjs snapshot-plan
node .opsx/tools/opsx-central-catalog.mjs snapshot-apply
node .opsx/tools/opsx-central-catalog.mjs index-plan
node .opsx/tools/opsx-central-catalog.mjs index-apply
```

Owner-facing commands:

- `/opsx-meta-update-snapshot` → snapshot-plan / snapshot-apply
- `/opsx-meta-update-index` → index-plan / index-apply

Config / shared process allowlist SoT: `.opsx/sources.yaml`

Same `allowlist` + `hard_exclude` are authoritative for:

- `/opsx-meta-commit` (IN-SCOPE)
- `/opsx-commit` (process OUT-OF-SCOPE → redirect to meta-commit)
- `/opsx-meta-update-snapshot` (central publish of committed allowlisted tree)

Do not maintain a second path list inside command bodies.

## Provider-run guard (fail-closed)

`opsx_provider_run_guard.py` — verify INDEPENDENT_REAUDIT fingerprints and
one-shot authorization before any provider pytest. Env
`AUTHORIZE_ONE_LIVE_RUN` must match packet `one_shot_authorization_id`
(SHA-256 of token). Only `AUTHORIZED_UNUSED` may spawn; consumption is
claimed atomically via `O_CREAT|O_EXCL` under
`.opsx/runs/scenario-coverage/<change_id>/authorizations/<one_shot_authorization_id>.json`
at spawn boundary (not rolled back on pytest failure). After spawn, an immutable
`<one_shot_authorization_id>.run_result.json` receipt records terminal guard
status, `provider_spawned`, `spawn_count`, `provider_return_code`, and
`provider_result` (no secrets). A consumption ledger without a matching receipt
yields `CERTIFICATION_EVIDENCE_CONFLICT` on verify (fail closed). Child pytest inherits
the parent process environment (PATH, Poetry) and receives audited test DB /
Redis coordinates from the packet (overriding conflicting parent values).

```bash
export AUTHORIZE_ONE_LIVE_RUN='<owner-secret>'
poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet packet.json --repo .
poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet packet.json
```

Packets include explicit `pytest_targets` (POSIX repo paths). Verification uses
`PurePosixPath` so Windows cannot fail on backslash parents. Frozen run block
must list targets, `# CANONICAL_PYTEST_ARGV_SHA256`, and `guard verify` →
`guard run` only (no executable pytest in the block; provider argv is packet-only).

Seal untracked packet at current HEAD (after pull, before live run):

```bash
export AUTHORIZE_ONE_LIVE_RUN='<owner-secret>'
poetry run python .opsx/tools/opsx_seal_provider_packet.py --live-token "$AUTHORIZE_ONE_LIVE_RUN"
```

`run` maps provider subprocess exit: `PROVIDER_PASSED` (0), `PROVIDER_FAILED` (5),
`PROVIDER_ERROR` (6). Authorization stays `AUTHORIZED_CONSUMED` after spawn even
on failure.

Non-consuming preflight: `opsx_provider_preflight.py` (imports, docker, collect-only).

`--require-docker-daemon` (used inside the sealed block, before `guard run`) also fails closed on:
Low-integrity process token, Low-labelled `.venv` launchers, `docker info` denied from the venv
python, hidden `git ls-files -v` flags, dirty worktree, stray `tests/tests`. `--fix-integrity`
tries `icacls <exe> /setintegritylevel M` first; a failure there is only a `WARN` (exit 1299 =
the calling token is Low and cannot raise labels).

### HOME-PC one-time machine fix (when the preflight reports `process_integrity: low`)

File labels cannot fix a Low *process token* (e.g. an agent sandbox shell). The Owner starts the
cert once from an ordinary Git Bash window (Start menu, not launched from the agent terminal),
confirms `whoami /groups | grep -i "Mandatory Label"` shows `Medium Mandatory Level`, that the
user is in `docker-users`, and that `docker info` works. Then run the sealed block there. No
tracked file is edited and nothing is marked assume-unchanged or deleted locally.

Unit tests: `tests/unit/opsx/test_opsx_provider_run_guard.py`.
