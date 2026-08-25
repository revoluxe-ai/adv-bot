# T11 — scenario plan evidence missing

## Given

Change requires scenario coverage (PA / Derived Lifecycle / material
Spec Scenarios). Authoritative design+specs exist. No durable files at:

```text
openspec/changes/<change>/scenario-coverage/plan.md
openspec/changes/<change>/scenario-coverage/plan.receipt.json
```

Chat may contain a prior `SCENARIO_COVERAGE_PLAN` with `PLAN_STATUS: ready`.

## When

`/opsx-continue` or `/opsx-ff` attempts task generation readiness.

## Expected

```text
TASKS_STATUS: BLOCKED
REASON: SCENARIO_PLAN_EVIDENCE_MISSING
SCENARIO_REQUIREMENTS_CONSUMED: no   # or omit yes
FILES_CHANGED: none
NEXT: /opsx-spec-scenario-coverage mode=plan change=<change>
```

## Forbidden

```text
SCENARIO_REQUIREMENTS_CONSUMED: yes
TASKS_STATUS: READY
trusting chat-only plan as SoT
manufacturing plan.receipt.json from task generation
```
