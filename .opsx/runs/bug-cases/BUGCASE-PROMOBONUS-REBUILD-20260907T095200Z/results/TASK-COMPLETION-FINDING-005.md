# Task completion evidence: FINDING-005

## Decision

- COMPLETION_DECISION: `NO_TASK_UPDATE`
- TASK_IDS: `[]`
- TASK_DELTA: No OpenSpec task was marked complete.
- FINDING_TERMINAL: no
- MISSION_COMPLETE: no
- NEXT_ACTION: BOUNDED_HUNTER

## Basis

`results/GREEN-FINDING-005.md` (GREEN_CONFIRMED) and `results/FIX-FINDING-005.md` prove leftover-fraction uses remaining over the top-up unit (`tranche.amount`), not `budget_after` or `campaign_budget_total`. Leftover remaining 200 with amount 1000 and budget_after 12000 yields fraction 0.2 (`M=1.25`), not `200/12000` (frozen node GREEN_CONFIRMED). RED recorded the pre-fix collapse (`assert Decimal('0.0166...') == Decimal('0.2')`). Frozen test SHA matches RED (`d2b77e376699bfe70729aec6a028759353a20d1a6d4a35fef2dfdce3532954a9`).

No existing OpenSpec `tasks.md` checkbox tracks FINDING-005 or this leftover-fraction denominator. Active and archived change tasks under `openspec/changes/**/tasks.md` were searched for `FINDING-005`, `leftover-fraction`, `leftover_fraction`, `tranche.amount`, `campaign_ledger`, `promo_accounting`, `budget_after`, and `leftover`; zero hits for this finding. Neighboring promo/pause/overspend wording in other changes is unrelated and was not closed. No checkbox was invented. Same decision as ROOT-001 / FINDING-002 / HC-001 / FINDING-004 hops (`NO_TASK_UPDATE`).

ROOT-001, FINDING-002, HC-001, FINDING-003, FINDING-004, and HC-FINDING-004-STALE-TEST were not reopened or closed. Intake item 6 was not started.

## Evidence

- `results/RED-FINDING-005.md` RED_CONFIRMED
- `results/FIX-FINDING-005.md`
- `results/GREEN-FINDING-005.md` GREEN_CONFIRMED
- Frozen node: `tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after` PASSED
- Adjacent file `tests/unit/wb/utils/test_promo_accounting.py`: 7 passed, 1 warning
- OpenSpec `tasks.md` edits: none

## Search (zero hits for this finding)

Corpus: `openspec/changes/**/tasks.md` (active + archive).

| Term | Hits in tasks.md |
|---|---|
| FINDING-005 | 0 |
| leftover-fraction | 0 |
| leftover_fraction | 0 |
| tranche.amount | 0 |
| campaign_ledger | 0 |
| promo_accounting | 0 |
| budget_after | 0 |
| leftover | 0 |

Unrelated neighboring strings (not marked complete): `overspend/PFO-max guard` in `openspec/changes/archive/2026-08-03-card-ab-hold-mode/tasks.md`; `Emergency stops spend` / `promotion pause adapters` in `openspec/changes/ab-hold-emergency-kill-switch/tasks.md`.

## Do not close

- ROOT-001
- FINDING-002
- HC-001
- FINDING-003
- FINDING-004
- HC-FINDING-004-STALE-TEST
- intake item 6
- this finding (FINDING_TERMINAL=no; no close)
