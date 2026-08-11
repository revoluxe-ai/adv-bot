# T1 — plan materialization COMMITTED

## Given

Valid Change requiring scenario coverage; planning artifacts present.

## When

```text
/opsx-spec-scenario-coverage mode=plan change=<change>
```

## Expected

```text
PLAN_STATUS: ready | provisional
MATERIALIZATION_STATUS: COMMITTED | ALREADY_CURRENT
human plan exists: .../scenario-coverage/plan.md
machine receipt exists: .../scenario-coverage/plan.receipt.json
PLAN_EVIDENCE_ID present
```
