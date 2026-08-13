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
