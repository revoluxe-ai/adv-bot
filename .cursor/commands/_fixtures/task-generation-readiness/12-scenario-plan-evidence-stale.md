# T12 — scenario plan evidence stale

## Given

Durable `scenario-coverage/plan.md` + `plan.receipt.json` exist with
`PLAN_STATUS: ready`, but `INPUTS.DESIGN_REVISION.content_hash` (or a
`SPEC_REVISION` hash) does not match the current authoritative file(s).

## When

Task generation readiness runs.

## Expected

```text
TASKS_STATUS: BLOCKED
REASON: SCENARIO_PLAN_EVIDENCE_STALE
SCENARIO_PLAN_FRESHNESS: stale
FILES_CHANGED: none
NEXT: /opsx-spec-scenario-coverage mode=plan change=<change>
```

## Forbidden

```text
SCENARIO_REQUIREMENTS_CONSUMED: yes
TASKS_STATUS: READY
accepting STALE receipt as CURRENT
rewriting receipt from continue/ff
```
