# Independent re-review — `/opsx-resolve-conflict` 0.39.0

Author: **Cursor**  
Status: `preview_only_no_go` · `GO_CAPABILITY=false` · `SAFE_USAGE_SCOPE=PREVIEW_ONLY`  
Platform: **Windows only** (ADR-OPSX-RC-PLATFORM-001 / WINDOWS_PREVIEW_ONLY)

## Architect-closed, pending reviewer confirmation

- R25-HIGH-001
- R25-HIGH-002
- R25-HIGH-003
- R25-MEDIUM-001
- R25-MEDIUM-003 (R30/R31 OS trust-store path protection + per-right AccessCheck)
- R25-MEDIUM-004 (R32 portability + Windows PREVIEW_ONLY ADR)
- R33-GATE-PROCESS-001 (immutable PREVIEW evidence — closed in R38)
- R38-GATE-PROCESS-001 (PREVIEW evidence path sanitization — closed in R39)

## Still open

- R25-MEDIUM-002 (trusted-Git boundary is **not** atomic)
- R25-PROCESS-001
- R33-GATE-PROCESS-002 (inner/outer platform matrix evidence-identical)
- `BLOCKER_AUTHORITY_PRODUCER_MISSING`
- `BLOCKER_OS_SANDBOX_RUNNER_MISSING`

## Critical fixes claimed (R39)

1. R39: tokenize trusted-Git paths to `<TRUSTED_GIT_EXECUTABLE>` in shipped PREVIEW evidence
2. R39: recursive JSON string-value path scan (closes R38 JSON-escaping bypass)
3. R39: rebuild real merge/rebase PREVIEW evidence without author-profile paths
4. R38 real PREVIEW evidence + FIXTURE_SETUP / command_ledger separation retained
5. R37 preview runtime hashes remain byte-identical; GO_CAPABILITY remains false

## Single delivery archive

- `<NATIVE_ARTIFACT_ROOT>/OPSX_RESOLVE_CONFLICT_COMMAND_001_R39_REVIEW_BUNDLE.zip`
- `OPSX_RESOLVE_CONFLICT_COMMAND_001_R39.TEST_REPORT.json`
- `OPSX_RESOLVE_CONFLICT_COMMAND_001_R39.SIDECAR.json`
- `OPSX_RESOLVE_CONFLICT_COMMAND_001_R39.PLATFORM_CAPABILITY_MATRIX.json`
