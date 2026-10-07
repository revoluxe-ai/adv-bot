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

`opsx_provider_run_guard.py` — verify INDEPENDENT_REAUDIT fingerprints before
any authorized provider pytest (`AUTHORIZE_ONE_LIVE_RUN`). Mismatch →
`BLOCKED_FINGERPRINT_MISMATCH`, spawn count 0.

```bash
poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet packet.json --repo .
poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet packet.json --dry-run
```

Unit tests: `tests/unit/opsx/test_opsx_provider_run_guard.py`.
