# Fixture T12 — repair loop

## Given

1. Package matches T2 (MUST→MAY in design; tasks inherit MAY).
2. Review emits `REPAIR_REQUIRED` + `PLANNING_REVIEW_HANDOFF`.
3. `/opsx-update` repairs `FIRST_BAD_ARTIFACT` (design) and stale
   downstream (tasks) per handoff — no scope expansion.
4. Re-run `/opsx-planning-review`.

## Expected (after successful repair)

```text
STATUS: PASS
APPLY_PLANNING_GATE: PASS
BLOCKING_FINDINGS: none
FILES_CHANGED: none
```

If repair incomplete, second review MUST still FAIL with remaining
findings — never PASS on hope.
