# 04_DECISION_LOG — platform & preview (R39)

## ADR-OPSX-RC-PLATFORM-001

| Field | Value |
|---|---|
| Decision | WINDOWS_PREVIEW_ONLY |
| Supported | windows |
| Unsupported | linux, macos |
| Operational scope | PREVIEW_ONLY |
| GO_CAPABILITY | false |
| Final decision owner | human user |

### Alternatives

| Option | Outcome |
|---|---|
| WINDOWS_PREVIEW_ONLY | Accepted |
| REQUIRE_CROSS_PLATFORM_SUPPORT | Rejected for this package line |
| Enable GO without producer/sandbox | Rejected |

### Consequences

- Platform matrix: windows `PREVIEW_ONLY_VERIFIED`; linux/macos `UNSUPPORTED`
- Non-Windows: `UNSUPPORTED_PLATFORM` before repo subprocesses
- Preview may run without authority producer / OS_VERIFIED sandbox with disclosure
- Linux/macOS enablement requires a separate architecture-change request
- Does **not** close R25-MEDIUM-002 or R25-PROCESS-001
