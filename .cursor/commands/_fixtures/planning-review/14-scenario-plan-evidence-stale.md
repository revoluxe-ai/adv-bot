# Fixture T14 — scenario plan evidence stale

## Given

Durable `plan.md` + `plan.receipt.json` exist with prior `PLAN_STATUS: ready`,
but receipt `INPUTS.DESIGN_REVISION` or `SPEC_REVISION` hash ≠ current
authoritative file(s).

## Expected

```text
STATUS: BLOCKED | REPAIR_REQUIRED
TYPE: STALE_DERIVED_ARTIFACT
OWNER_INPUT_REQUIRED: NO
NEXT: /opsx-spec-scenario-coverage mode=plan change=<change>
FILES_CHANGED: none
```

## Forbidden

```text
PASS on STALE receipt
silently accepting old PLAN_EVIDENCE_ID after design/spec change
```
