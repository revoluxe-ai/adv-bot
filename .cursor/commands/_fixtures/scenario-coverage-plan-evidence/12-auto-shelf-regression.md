# T12 — auto-shelf-exhausted-pause-retest regression

## Change

`auto-shelf-exhausted-pause-retest`

## When (after process fix applied)

```text
/opsx-spec-scenario-coverage mode=plan change=auto-shelf-exhausted-pause-retest
```

## Expected

```text
~18 Spec Scenarios represented
Lifecycle L1–L6 covered in LIFECYCLE_COVERAGE
PLAN_STATUS: ready
MATERIALIZATION_STATUS: COMMITTED | ALREADY_CURRENT
durable:
  openspec/changes/auto-shelf-exhausted-pause-retest/scenario-coverage/plan.md
  openspec/changes/auto-shelf-exhausted-pause-retest/scenario-coverage/plan.receipt.json
```

Then fresh process:

```text
/opsx-planning-review change=auto-shelf-exhausted-pause-retest
```

MUST NOT block solely because scenario plan existed only in a prior chat.

## Forbidden in this process fix

```text
manually patching product tasks.md / design / spec as the repair
weakening planning-review to trust self-attestation without receipt
```
