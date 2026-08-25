# 07 — T8 route contract conflict

## Ambiguous / contradictory packet

```text
EXPECTED_NEXT_COMMAND: /opsx-fix-bug
PROSE_STOP: must run /opsx-test RED first before any /opsx-fix-bug
PRECONDITIONS missing OR PRECONDITIONS.RED_REQUIRED=yes with NEXT=/opsx-fix-bug
  without GO_TOKEN=FORBIDDEN clarification
```

Canonical resolve when producer emits complete ROUTE_TRANSITION with
GO_TOKEN=FORBIDDEN → ADVANCE to /opsx-fix-bug WITHOUT GO (not conflict).

## Expected when still contradictory

```text
PAUSED
ROUTE_CONTRACT_CONFLICT
NO guessed NEXT_COMMAND (/opsx-fix-bug vs /opsx-test)
identify producing command/contract
```
