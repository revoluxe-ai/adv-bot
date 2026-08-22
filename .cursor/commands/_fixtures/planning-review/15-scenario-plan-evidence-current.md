# Fixture T15 — scenario plan evidence current

## Given

Required scenario coverage. Durable CURRENT pair with integrity-ok receipt
(`PLAN_CONTENT_HASH` matches `plan.md`; INPUTS match current design/specs).
`PLAN_STATUS: ready`. Lifecycle L* represented; no unresolved material gaps.
Other pillars PASS.

## Expected

```text
SPEC_COVERAGE: PASS
STATUS: PASS   # when P1–P8 otherwise pass
APPLY_PLANNING_GATE: PASS
FILES_CHANGED: none
```

P6 consumes durable evidence without pasted chat plan and without rebuilding
the scenario matrix.

## Forbidden

```text
BLOCKED solely because evidence lived only in a prior chat
rebuilding full scenario matrix as a substitute for reading plan.md
```
