# 13 — T14 Route B follows envelope

```text
CLASSIFY: SPEC_GAP
CHOSEN_ROUTE: ROUTE_B
ROUTE_TRANSITION.NEXT_COMMAND: /opsx-update
TO_STATE: AWAITING_SPEC_UPDATE
```

## Expected

```text
dispatch /opsx-update
MUST NOT hardcode Route A /opsx-fix-bug
supervisor policy has no route_b_next option
```
