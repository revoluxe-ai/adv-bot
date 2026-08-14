# Fixtures: durable scenario-coverage plan evidence

Process regression for materializing `/opsx-spec-scenario-coverage mode=plan`
as Change-local durable evidence consumed by task generation and
`/opsx-planning-review` P6.

Authority:

- `.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md` → DURABLE_PLAN_EVIDENCE
- `.cursor/pipeline/contracts/TASK_GENERATION.md` §6
- `.cursor/pipeline/contracts/PLANNING_REVIEW.md` P6

Canonical paths:

```text
openspec/changes/<change>/scenario-coverage/plan.md
openspec/changes/<change>/scenario-coverage/plan.receipt.json
```

Sole writer: `/opsx-spec-scenario-coverage mode=plan`.

## Index (acceptance T1–T12)

| ID | File | Theme |
|----|------|-------|
| 01 | `01-materialization-committed.md` | T1 COMMITTED pair |
| 02 | `02-fresh-process-discoverability.md` | T2 planning-review fresh chat |
| 03 | `03-tasks-consume-receipt.md` | T3 PLAN_EVIDENCE_ID |
| 04 | `04-missing-receipt-blocks-tasks.md` | T4 MISSING |
| 05 | `05-stale-design.md` | T5 STALE design |
| 06 | `06-stale-spec.md` | T6 STALE spec |
| 07 | `07-rerun-supersedes.md` | T7 replace CURRENT |
| 08 | `08-idempotency.md` | T8 same hash |
| 09 | `09-materialization-failed.md` | T9 no false READY |
| 10 | `10-body-receipt-integrity.md` | T10 INTEGRITY_FAIL |
| 11 | `11-receipt-input-tamper.md` | T11 STALE/INVALID |
| 12 | `12-auto-shelf-regression.md` | T12 live Change regression |

## Forbidden

- chat as SoT for gate consumption
- consumers manufacturing receipts
- product artifact rewrites as the process fix
- `.tmp` as canonical plan SoT
