# Fixtures: Derived Lifecycle → Spec → Scenario Coverage

Process-only regression for the pipeline:

```text
owner-contract-review PASS
  → continue | ff  (DERIVED Lifecycle in design)
  → spec scenarios covering L*
  → /opsx-spec-scenario-coverage mode=plan
```

Commands under test:

- `/opsx-continue` / `/opsx-ff` (lifecycle derivation)
- `/opsx-spec-scenario-coverage` (LIFECYCLE ↔ SPEC; no second Owner confirm)
- contracts: `PRODUCT_ACCEPTANCE.md`, `SCENARIO_TEST_COVERAGE.md`

## Authority invariant

```text
Owner Contract = semantic authority
Derived Lifecycle = planning representation (no new product authority)
scenario-coverage = verifier only
```

`CONFIRM_LIFECYCLE` / mandatory `OWNER_LIFECYCLE_ECHO` are **legacy-only**
(Changes without reviewed `owner-contract.md`).

## Index

| ID | File | Theme | Expected |
|----|------|-------|----------|
| 01 | `01-continue-derives-lifecycle.md` | T1 | design DERIVED; no Owner confirm ask |
| 02 | `02-ff-equivalence.md` | T2 | ff lifecycle ≡ continue |
| 03 | `03-missing-scenario.md` | T3 | SPEC_SCENARIO_MISSING; not NEEDS_OWNER |
| 04 | `04-unresolved-semantics.md` | T4 | UNRESOLVED_PRODUCT_SEMANTICS → owner-contract-review |
| 05 | `05-no-echo-ceremony.md` | T5 | plan works without OWNER_LIFECYCLE_ECHO/CONFIRM |
| 06 | `06-semantic-drift.md` | T6 | SEMANTIC_DRIFT; not PASS |
| 07 | `07-planning-lifecycle-gap.md` | T7 | PLANNING_LIFECYCLE_GAP; not re-quiz Owner |
| 08 | `08-non-temporal.md` | T8 | no forced 3–7 ceremonial lifecycle |
| 09 | `09-auto-shelf-exhausted-pause-retest-plan.md` | real Change | no BLOCKED_NEEDS_OWNER_LIFECYCLE; durable plan+receipt when ready |

Also see sibling suite
`.cursor/commands/_fixtures/scenario-coverage-plan-evidence/` for
materialization / freshness / consumer discoverability (T1–T12).

## Forbidden outcomes (any fixture with reviewed Owner Contract)

- `BLOCKED_NEEDS_OWNER_LIFECYCLE` solely because echo/CONFIRM absent
- `CONFIRM_LIFECYCLE` as a second semantic gate
- inventing product transitions when Owner Contract is silent
- claiming `PLAN_STATUS: ready` for gate consumption without durable
  `scenario-coverage/plan.md` + `plan.receipt.json`
