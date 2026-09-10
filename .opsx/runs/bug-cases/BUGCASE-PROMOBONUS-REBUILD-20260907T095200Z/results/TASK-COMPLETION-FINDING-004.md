# Task completion evidence: FINDING-004

## Decision

- COMPLETION_DECISION: `NO_TASK_UPDATE`
- TASK_IDS: `[]`
- TASK_DELTA: No OpenSpec task was marked complete.
- FINDING_TERMINAL: no
- MISSION_COMPLETE: no
- NEXT_ACTION: bounded hunt

## Basis

`results/GREEN-FINDING-004.md` (GREEN_CONFIRMED) and `results/FIX-FINDING-004.md` prove `apply_spend_fefo` skips expired leftover in the spend loop; expired leftover 300 + live leftover 200 + spend 50 yields remaining 150 (frozen node GREEN_CONFIRMED). RED recorded the pre-fix inflation (`assert 200 == 150`). Frozen test SHA matches RED (`cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2`).

No existing OpenSpec `tasks.md` checkbox tracks FINDING-004 or this FEFO expired-leftover spend skip. Active and archived change tasks under `openspec/changes/**/tasks.md` were searched for `FINDING-004`, `apply_spend_fefo`, `promo_accounting`, `fefo_spend`, and `leftover`; zero hits for this finding. Neighboring "spend"/"overspend" wording in other changes (AB-hold emergency pause; archived card-ab-hold overspend guard) is unrelated and was not closed. No checkbox was invented. Same decision as ROOT-001 / FINDING-002 / HC-001 hops (`NO_TASK_UPDATE`).

ROOT-001, FINDING-002, HC-001, and FINDING-003 were not reopened or closed. Intake items 5-6 were not started.

## Evidence

- `results/RED-FINDING-004.md` RED_CONFIRMED
- `results/FIX-FINDING-004.md`
- `results/GREEN-FINDING-004.md` GREEN_CONFIRMED
- Frozen node: `tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired` PASSED
- Adjacent file `tests/unit/wb/utils/test_promo_accounting.py`: 1 failed, 5 passed (sibling `test_fefo_spend_and_expired_tranche_unusable` still asserts remaining==200; bug-encoding; not closed or edited)
- OpenSpec `tasks.md` edits: none

## Search (zero hits for this finding)

Corpus: `openspec/changes/**/tasks.md` (active + archive).

| Term | Hits in tasks.md |
|---|---|
| FINDING-004 | 0 |
| apply_spend_fefo | 0 |
| promo_accounting | 0 |
| fefo_spend | 0 |
| leftover | 0 |

Unrelated neighboring strings (not marked complete): `overspend/PFO-max guard` in `openspec/changes/archive/2026-08-03-card-ab-hold-mode/tasks.md`; `Emergency stops spend` / `promotion pause adapters` in `openspec/changes/ab-hold-emergency-kill-switch/tasks.md`.

## Do not close

- ROOT-001
- FINDING-002
- HC-001
- FINDING-003
- intake items 5-6
- sibling `test_fefo_spend_and_expired_tranche_unusable` (bug-encoding; not a mapped OpenSpec task)
