# T2 — fresh-process discoverability

## Given

T1 succeeded (durable CURRENT plan+receipt). New independent chat/process
with no prior scenario plan paste.

## When

```text
/opsx-planning-review change=<change>
```

## Expected

```text
P6 locates durable plan.md + plan.receipt.json
no demand to paste chat SCENARIO_COVERAGE_PLAN
SPEC_COVERAGE not BLOCKED solely for missing chat evidence
```
