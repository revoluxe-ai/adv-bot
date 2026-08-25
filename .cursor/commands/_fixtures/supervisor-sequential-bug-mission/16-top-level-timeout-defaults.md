# 16 — Top-level Task timeout defaults (SUP-DEF-001)

```text
DISPATCH: any primary /opsx-* via Supervisor Task
TIMEOUT / HEARTBEAT / NO_PROGRESS / STOP_ACK: empty or omitted
```

## Expected

```text
CONTRACT_VIOLATION if clocks empty
ordinary hop must use §12.0 defaults (TIMEOUT=1800 NO_PROGRESS=600 …)
/opsx-bug-team|/opsx-static-check must use orchestrator defaults
  (TIMEOUT=3600 NO_PROGRESS=900 …)
unbounded sync wait: FORBIDDEN
```
