# T7 — rerun after stale

## Given

STALE prior CURRENT pair (after design/spec change).

## When

```text
/opsx-spec-scenario-coverage mode=plan change=<change>
```

## Expected

```text
new CURRENT evidence (COMMITTED)
single canonical pair under scenario-coverage/
old PLAN_EVIDENCE_ID no longer CURRENT
consumers accept new receipt
```
