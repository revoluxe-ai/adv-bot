# T9 / PART F — auto-shelf-exhausted-pause-retest plan regression

## Change

`auto-shelf-exhausted-pause-retest`

## Given (process expectation)

- Reviewed Owner Contract semantics available under
  `openspec/changes/auto-shelf-exhausted-pause-retest/owner-contract.md`
- Planning artifacts (proposal/decision/design/spec) present
- Lifecycle uniquely follows from reviewed Owner semantics (PART F)
- `OWNER_LIFECYCLE_ECHO` / `CONFIRM_LIFECYCLE` may be absent

## Derived lifecycle (expected shape — not product invent)

```text
L1  «Управление ставкой в полках» ON AND main bid = Best plan
L2  Auto works; shelf module tests bids
L3  Epoch exhausted: no new bids to test AND no qualified-tested fit
    under current resolve CPO
L4  shelf-exhausted pause block; distinct reason + resolve CPO kind/value
L5  While our block active: each tick re-resolve CPO and recheck tested points
L6  Our block clears on: fit | calendar retest due | «Сбросить паузу»
    Clear MUST NOT force-start Auto
L7  If no other blockers → Auto actually starts → new testing epoch
    If other blockers remain → Auto stays paused → new epoch not yet started
```

Cross-cutting:

```text
With shelf module ON, mid-cycle cost_rule_failed pause MUST NOT stop Auto.
```

## When

```text
/opsx-spec-scenario-coverage mode=plan change=auto-shelf-exhausted-pause-retest
```

## Expected

```text
MUST NOT return:
  BLOCKED_NEEDS_OWNER_LIFECYCLE
  OWNER_LIFECYCLE_ECHO: MISSING
  CONFIRM_LIFECYCLE absent  (as blocking reason on primary path)

MUST return one of:
  STATUS: ORIENTED | READY   + SCENARIO_COVERAGE_PLAN / LIFECYCLE_COVERAGE
  STATUS: GAP                + SPEC_SCENARIO_MISSING / SPEC_COVERAGE_GAP /
                               PLANNING_LIFECYCLE_GAP / SEMANTIC_DRIFT
                               (if artifacts truly incomplete)
```

## Note

This fixture documents the **process** regression. It does not rewrite the
product Change artifacts. If design lacks an explicit `## Lifecycle` section,
scenario-coverage may derive L* from owner-contract + planning without
asking Owner again — or emit `PLANNING_LIFECYCLE_GAP` for the planning writer.
