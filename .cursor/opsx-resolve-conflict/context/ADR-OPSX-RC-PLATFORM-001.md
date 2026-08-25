# ADR-OPSX-RC-PLATFORM-001 — Platform support scope

**Decision ID:** ADR-OPSX-RC-PLATFORM-001  
**Disposition:** WINDOWS_PREVIEW_ONLY  
**Package line:** OPSX_RESOLVE_CONFLICT_COMMAND_001 (R33+)

## Decision

Windows is the only supported platform. Operational scope is **PREVIEW_ONLY**.

- Linux and macOS are explicitly **UNSUPPORTED**.
- Non-Windows execution fails closed with typed reason `UNSUPPORTED_PLATFORM`
  before repository subprocesses.
- Preview may run without authority producer / OS_VERIFIED sandbox; absence is
  disclosed in LIMITATIONS.
- Preview never writes worktree/index/refs and never enables GO.
- Linux/macOS enablement requires a separate architecture-change request.

## Alternatives considered

| Option | Outcome |
|---|---|
| WINDOWS_PREVIEW_ONLY | Accepted |
| REQUIRE_CROSS_PLATFORM_SUPPORT | Rejected for this package line |

## Consequences

- Platform matrix: windows `PREVIEW_ONLY_VERIFIED`; linux/macos `UNSUPPORTED`
- Does not close R25-MEDIUM-002 or R25-PROCESS-001
- GO_CAPABILITY remains false
