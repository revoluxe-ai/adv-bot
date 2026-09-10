# Task completion evidence: HC-FINDING-004-STALE-TEST

## Decision

- COMPLETION_DECISION: `NO_TASK_UPDATE`
- TASK_IDS: `[]`
- TASK_DELTA: No OpenSpec task was marked complete.
- FINDING_TERMINAL: no
- MISSION_COMPLETE: no
- NEXT_ACTION: INTEGRATION_OPERATOR

## Basis

`results/GREEN-HC-FINDING-004-STALE-TEST.md` (GREEN_CONFIRMED) and `results/FIX-HC-FINDING-004-STALE-TEST.md` prove the stale sibling assertion was corrected: `test_fefo_spend_and_expired_tranche_unusable` now expects remaining 150 (expired leftover 300 + live leftover 200 + spend 50). Production `promo_accounting.py` was already skip-expired and was not edited. FINDING-004 frozen node still passes.

No existing OpenSpec `tasks.md` checkbox tracks HC-FINDING-004-STALE-TEST or this stale-assertion repair. Active and archived change tasks under `openspec/changes/**/tasks.md` were searched for `HC-FINDING-004-STALE-TEST`, `HC-FINDING-004`, `apply_spend_fefo`, `promo_accounting`, `fefo_spend`, `leftover`, and `test_fefo_spend_and_expired`; zero hits. No checkbox was invented. Same decision as FINDING-004 / ROOT-001 / FINDING-002 / HC-001 hops (`NO_TASK_UPDATE`).

ROOT-001, FINDING-002, HC-001, FINDING-003, and FINDING-004 were not reopened or closed. Intake items 5-6 were not started. Finding was not closed.

## Evidence

- `results/RED-HC-FINDING-004-STALE-TEST.md` RED_CONFIRMED
- `results/FIX-HC-FINDING-004-STALE-TEST.md` FIX_APPLIED (test-only; production unchanged)
- `results/GREEN-HC-FINDING-004-STALE-TEST.md` GREEN_CONFIRMED
- Frozen node: `tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable` PASSED
- Adjacent file `tests/unit/wb/utils/test_promo_accounting.py`: 6 passed (FINDING-004 node `test_fefo_spend_hits_live_leftover_not_expired` still PASSED)
- TEST_CONTENT_SHA256 post-fix: `233084e637cfaa1f4c3ac5bea151f5f1cb8a377f6f30b286ac19f2bba9f50c53`
- OpenSpec `tasks.md` edits: none

## Search (zero hits for this finding)

Corpus: `openspec/changes/**/tasks.md` (active + archive).

| Term | Hits in tasks.md |
|---|---|
| HC-FINDING-004-STALE-TEST | 0 |
| HC-FINDING-004 | 0 |
| apply_spend_fefo | 0 |
| promo_accounting | 0 |
| fefo_spend | 0 |
| leftover | 0 |
| test_fefo_spend_and_expired | 0 |

## Do not close

- ROOT-001
- FINDING-002
- HC-001
- FINDING-003
- FINDING-004
- intake items 5-6
- this finding (FINDING_TERMINAL=no; no close)
