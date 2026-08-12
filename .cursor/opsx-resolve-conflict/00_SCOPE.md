# 00_SCOPE — Independent review scope (R39 / 0.39.0)

## In scope

- Packaged command: `candidate/.cursor/commands/opsx-resolve-conflict.md`
- Runtime under `runtime/opsx_conflict/**` (R30/R31 trust-store frozen for GO)
- Windows PREVIEW_ONLY advisory conflict analysis (`preview_advisory.py`)
- Exact operation-ID Git grammar (`preview_readonly_git.py`; R34 byte-frozen)
- Bounded repository context evidence (`preview_context.py`) + advisory reasoning
- Architecture baseline / workflow / handoff / decision docs
- Platform gate: Windows only; Linux/macOS UNSUPPORTED
- Evidence pipeline: ZIP + TEST_REPORT/SIDECAR/platform matrix

## Out of scope

- Automatic conflict resolution / worktree or index writes
- GO enablement (`GO_CAPABILITY` remains false)
- Authority producer implementation
- OS_VERIFIED sandbox implementation
- Linux or macOS enablement
- Changes to trusted-Git / authority / validation / trust-store GO architecture
- Claiming R25-MEDIUM-002 or R25-PROCESS-001 closed

## Operational scope

`SAFE_USAGE_SCOPE=PREVIEW_ONLY` — advisory analysis only; human applies changes.

## Author

Cursor (packaged for OPSX independent review).

## Prior package

`0.5.0`–`0.35.0` REJECTED or REVISION_REQUIRED — not in SAFE_TO_USE scope.
