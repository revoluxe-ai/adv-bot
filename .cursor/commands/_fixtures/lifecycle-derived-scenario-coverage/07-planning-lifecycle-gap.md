# T7 — lifecycle incomplete (planning gap)

## Given

- Owner Contract uniquely defines transition T
- `design.md` Derived Lifecycle omits T

## When

`/opsx-spec-scenario-coverage mode=plan`

## Expected

```text
GAP_TYPE: PLANNING_LIFECYCLE_GAP
REPAIR_TARGET: design (planning)
NEXT_ACTION: /opsx-continue | /opsx-ff | /opsx-update
```

## Forbidden

```text
NEEDS_OWNER
CONFIRM_LIFECYCLE
re-asking Owner to restate T
```
