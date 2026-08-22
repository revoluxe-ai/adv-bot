# Fixture T13 — scenario plan evidence missing

## Given

Scenario coverage is required. Package otherwise coherent. No durable:

```text
openspec/changes/<change>/scenario-coverage/plan.md
openspec/changes/<change>/scenario-coverage/plan.receipt.json
```

Owner is not asked to paste prior chat plan.

## Expected

```text
STATUS: BLOCKED
TYPE: SPEC_COVERAGE_EVIDENCE_MISSING
OWNER_INPUT_REQUIRED: NO
NEXT: /opsx-spec-scenario-coverage mode=plan change=<change>
FILES_CHANGED: none
```

## Forbidden

```text
PASS by trusting tasks.md SCENARIO_REQUIREMENTS_CONSUMED: yes
PASS by reconstructing matrix from chat
demanding Owner paste SCENARIO_COVERAGE_PLAN
```
