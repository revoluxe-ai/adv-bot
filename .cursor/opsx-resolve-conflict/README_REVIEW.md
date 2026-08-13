# Independent re-review — `/opsx-resolve-conflict` 0.40.0

Author: Cursor  
Status: `preview_only_no_go` · `GO_CAPABILITY=false` · `SAFE_USAGE_SCOPE=PREVIEW_ONLY`

## Why re-review

R39 closed R38-GATE-PROCESS-001 (PREVIEW evidence path sanitization). Independent
review of PR #432 / commit `e22993c4…` raised **BUGBOT-HIGH-002**: PREVIEW could
load multiple unmerged paths into report metadata while semantically analyzing
only `snapshots[0]`.

R40 makes the single-path contract explicit and fail-closed.

## Claimed closures

- BUGBOT-HIGH-002 (single-path PREVIEW contract — closed in R40)
- R38-GATE-PROCESS-001 (retained from R39)
- R33-GATE-PROCESS-001 (retained from R38)
- R36-GATE-AUTHORITY-002 / R35-GATE-AUTHORITY-001 (retained)

## Critical fixes claimed (R40)

1. Multi-conflict without `--path` → `PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS`
2. Successful PREVIEW binds analysis surfaces to exactly one selected path
3. Inventory fields explicitly labeled not-analyzed
4. R34 `preview_readonly_git.py` remains byte-identical
5. GO_CAPABILITY remains false

## Artifacts (after ship)

- `<NATIVE_ARTIFACT_ROOT>/OPSX_RESOLVE_CONFLICT_COMMAND_001_R40_REVIEW_BUNDLE.zip`
- `OPSX_RESOLVE_CONFLICT_COMMAND_001_R40.TEST_REPORT.json`
- `OPSX_RESOLVE_CONFLICT_COMMAND_001_R40.SIDECAR.json`
- `OPSX_RESOLVE_CONFLICT_COMMAND_001_R40.PLATFORM_CAPABILITY_MATRIX.json`
