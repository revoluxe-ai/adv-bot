# 02_REQUIRED_CONTEXT — R40

## Bundled in this package

- `candidate/.cursor/commands/opsx-resolve-conflict.md`
- `context/OPSX_CONTEXT_EXTRACT.md`
- `MANIFEST.json`, `CHANGELOG.md`, schemas, runtime, tests
- `00_SCOPE.md`, `01_REVIEW_STANDARD.md`, `03_VERDICT_SCHEMA.md`

## From host repository (when reviewing against live OPSX)

Exact paths from MANIFEST `required_repo_paths`, especially:

- `.cursor/commands/opsx-source-resolution.md`
- `.cursor/commands/opsx-execution-preflight.md`
- `.cursor/rules/testing-rules.mdc`
- `openspec/config.yaml`
- `openspec/policies/VERIFY_POLICY.md`
- `openspec/decisions/index.md`
- `.cursor/static-check/registry.yaml`
- `.cursor/pipeline/GRAPH.md` (advisory navigation only)
- `.cursor/opsx-review-commands`

## Lineage

`source_commit` in MANIFEST.json is authoritative for this package build.
Machine-readable mapping: `context/SOURCE_LINEAGE.json`.
External declaration producer contracts (when present on host):
- `openspec/policies/CONFLICT_AUTHORITY_PRODUCER.md`
- `openspec/policies/CONFLICT_AUTHORITY_ISSUERS.md`
- `.cursor/opsx-authority-producers.json`
