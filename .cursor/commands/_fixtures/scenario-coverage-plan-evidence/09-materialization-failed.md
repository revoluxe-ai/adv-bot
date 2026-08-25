# T9 — materialization failure

## Given

Analysis succeeds; write of plan.md and/or receipt fails mid-materialization.

## Expected

```text
MATERIALIZATION_STATUS: FAILED
PLAN_STATUS: NOT_COMMITTED   # must not become durable ready
no consumer-satisfying CURRENT pair
recovery: rerun mode=plan
```
