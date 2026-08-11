# T3 — tasks consume durable receipt

## Given

CURRENT durable plan receipt with `PLAN_STATUS: ready`.

## When

Task generation (`/opsx-continue` or `/opsx-ff`).

## Expected

```text
SCENARIO_REQUIREMENTS_CONSUMED: yes
SCENARIO_PLAN_EVIDENCE_ID matches receipt PLAN_EVIDENCE_ID
SCENARIO_PLAN_STATUS: ready
SCENARIO_PLAN_FRESHNESS: current
```
