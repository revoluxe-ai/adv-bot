# 03 — T3 worker PASS is not mission PASS

## Classify envelope

```text
COMMAND: /opsx-classify-bug
TERMINAL_STATUS: PASS
MISSION_COMPLETE: no
FINDING_TERMINAL: no
ROUTE_TRANSITION.NEXT_COMMAND: /opsx-fix-bug
PRECONDITIONS.GO_TOKEN: FORBIDDEN
```

## Expected

```text
mission remains ACTIVE
MISSION_COMPLETE: no
NEXT_COMMAND: /opsx-fix-bug (WITHOUT GO)
```
