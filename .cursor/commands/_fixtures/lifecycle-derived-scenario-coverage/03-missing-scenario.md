# T3 — missing scenario

## Given

- Derived Lifecycle present (e.g. L6 clear-by-button with other blocker)
- Matching Spec Scenario absent

## When

`/opsx-spec-scenario-coverage mode=plan change=<id>`

## Expected

```text
STATUS: GAP  (or PLAN with OPEN_QUESTIONS)
GAP_TYPE: SPEC_SCENARIO_MISSING | SPEC_COVERAGE_GAP
REPAIR_TARGET: spec
REPAIR_OWNER: /opsx-continue | /opsx-ff | /opsx-update
```

## Forbidden

```text
NEEDS_OWNER
BLOCKED_NEEDS_OWNER_LIFECYCLE
CONFIRM_LIFECYCLE
```
