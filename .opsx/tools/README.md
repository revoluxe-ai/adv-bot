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
written to `.opsx/runs/scenario-coverage/<change_id>/one_shot_authorization.json`
at spawn boundary (not rolled back on pytest failure). Child pytest inherits
the parent process environment (PATH, Poetry) and receives audited test DB /
Redis coordinates from the packet (overriding conflicting parent values).

```bash
export AUTHORIZE_ONE_LIVE_RUN='<owner-secret>'
poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet packet.json --repo .
poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet packet.json
```

Packets include explicit `pytest_targets` (POSIX repo paths). Verification uses
`PurePosixPath` so Windows cannot fail on backslash parents. Frozen run block
must list targets and `guard verify` → `guard run` only (no direct
`poetry run pytest` before guard).

Seal untracked packet at current HEAD (after pull, before live run):

```bash
export AUTHORIZE_ONE_LIVE_RUN='<owner-secret>'
poetry run python .opsx/tools/opsx_seal_provider_packet.py --live-token "$AUTHORIZE_ONE_LIVE_RUN"
```

Unit tests: `tests/unit/opsx/test_opsx_provider_run_guard.py`.
