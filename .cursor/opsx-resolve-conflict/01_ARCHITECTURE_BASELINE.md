# 01_ARCHITECTURE_BASELINE — OPSX resolve-conflict (R39)

## Decision

**ADR-OPSX-RC-PLATFORM-001 / WINDOWS_PREVIEW_ONLY**

| Field | Value |
|---|---|
| Supported platform | Windows |
| Unsupported | Linux, macOS |
| Operational scope | PREVIEW_ONLY |
| GO_CAPABILITY | false |
| Final decision owner | human user |

## Baseline change

The command may perform **advisory** conflict analysis on Windows without an
installed external authority producer or OS_VERIFIED sandbox.

Absence of those components is disclosed as analysis **LIMITATIONS**, not as a
hard STOP for preview.

## Hard prohibitions (architecture)

Preview must never:

- modify worktree bytes;
- modify index bytes;
- modify refs;
- stage files / create commits;
- run merge/rebase continue or abort;
- push;
- claim that a suggested resolution is independently authenticated or safe to apply.

## Frozen components

Trusted-Git architecture (`git_typed.py`), authority producer contract,
validation registry GO path, and OS trust-store remain frozen for GO. Preview
uses a separate read-only Git allowlist module and does not weaken those
surfaces.

## Related findings (remain open)

- R25-MEDIUM-002 — trusted-Git not claimed atomic
- R25-PROCESS-001 — pack/commit membership
- BLOCKER_AUTHORITY_PRODUCER_MISSING
- BLOCKER_OS_SANDBOX_RUNNER_MISSING
