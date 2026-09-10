# Closure evidence: FINDING-005

```text
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-005
SIBLING_FINDING_ID: none
BUG_FAMILY_ID: BFAM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-005/LEFTOVER-FRACTION-TRANCHE-AMOUNT
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-005/LEFTOVER-FRACTION-TRANCHE-AMOUNT
FINDING_STATUS: closed_fixed
EPISODE_TERMINAL: FIXED
CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A
FAMILY_STATUS: CLOSED_FIXED_VERIFIED
CLOSURE_STATUS: CLOSED_FIXED_VERIFIED
CASE_STATUS: OPEN_RESIDUAL_INTAKE
LEAVE_OPEN_REASON: partial_residual
RESIDUAL_INTAKE_ITEMS: 6
MISSION_COMPLETE: no
CONTROL_MODEL: USER_REVIEWS_UNCOMMITTED_WORKTREE
EXECUTION_MODE: CONTROLLED_LIVE_UNCOMMITTED
COMMIT_CREATED: NO
WORKTREE_STATUS: UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
USER_ACTION_REQUIRED: REVIEW_DIFF_AND_DECIDE_COMMIT
CLOSED_AT: 2026-09-07T20:12:45Z
WORKER_ID: CLOSURE_OPERATOR
WORKER_EXECUTION_ID: WEX/CLOSURE_OPERATOR/6c17d35dcf
ORCHESTRATION_ID: ORCH/sup-promo-t10-d10
CHECKPOINT_GENERATION: 72
```

## Hard gates

- HARD_BLOCK_READY / same-invariant candidate gate: PASS. Hunt CLEAR (`CANDIDATES=[]`). No HC sibling for FINDING-005. Scan of `findings/` for `STATUS ∈ {open_candidate, OPEN_CANDIDATE}`: none. `OPEN_SAME_INVARIANT_CANDIDATES=NONE`.
- Episode FANIN gate: PASS. `results/FANIN.md` STATUS=`FANIN_READY`, `HARD_BLOCK_READY=false`, `BLOCKING_FINDINGS=[]`, `CLOSURE_READINESS=READY_FOR_CLOSURE`, residual `[6]`.
- Root fix/green: PASS. FINDING-005 leftover-fraction `GREEN_CONFIRMED` (`results/GREEN-FINDING-005.md`, `results/FIX-FINDING-005.md`). Frozen node `tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after` PASSED. `TEST_CONTENT_SHA256` `d2b77e376699bfe70729aec6a028759353a20d1a6d4a35fef2dfdce3532954a9`. No sibling. Not FALSE_POSITIVE. Not OUT_OF_SCOPE.
- Learning gate: PASS. `runtime.learning_decision.evaluate_closure_learning_gate` → PASS on `family/LEARNING_DECISION.json`. `LEARNING_STAGE_INVOKED=true`, `LEARNING_VERDICT=LOCAL_CASE_NOTE_ONLY`, `LEARNING_STATUS=COMPLETE`, `PROMOTION_DECISION=RESOLVED_NO_PROMOTE`, `DECISION_HASH` `3f872baa7927b47b6f10e85f7a4d6a8970ee485797f784f727af8e2b5b449b95`. Closure-allowed without promotion.

## What closed

FINDING-005 is `closed_fixed` / `EPISODE_TERMINAL=FIXED` / `CLASSIFICATION=IMPLEMENTATION_BUG` / `ROUTE_A`. Family `BFAM/.../LEFTOVER-FRACTION-TRANCHE-AMOUNT` members `[FINDING-005]` is `CLOSED_FIXED_VERIFIED`. No hunt sibling.

Invariant: campaign leftover fraction must use remaining over the top-up unit (`tranche.amount`), not `budget_after` or `campaign_budget_total`. Leftover remaining 200 with amount 1000 and budget_after 12000 must yield fraction 0.2 (`M=1.25`), not `200/12000`. Production mix now uses `tranche.amount`.

## What did not close

The CASE stays open (`OPEN_RESIDUAL_INTAKE` / `partial_residual`). INTAKE-001 residual item 6 remains unmaterialized. FINDING-006 was not created. `MISSION_COMPLETE: no`.

ROOT-001 remains `closed_fixed`. FINDING-002 and HC-001 remain `closed_fixed`. FINDING-003 remains `closed_false_positive`. FINDING-004 and HC-FINDING-004-STALE-TEST remain `closed_fixed`. This hop did not reopen them and did not overwrite `family/closed/FINDING-004/`, `family/closed/FINDING-002/`, or `family/closed/ROOT-001/`.

## Closure operator did not

Change production code, tests, OpenSpec, `results/FANIN.md`, or `family/LEARNING_DECISION.json`. Did not git commit, push, or deploy. Did not start intake item 6. Did not allocate FINDING-006. Did not paste `mode=resume-family-fanout`. Did not call `runtime.control_model.apply_closure_artifacts`.

## Evidence paths

- `results/RED-FINDING-005.md`
- `results/FIX-FINDING-005.md`
- `results/GREEN-FINDING-005.md`
- `results/FANIN.md`
- `family/FAMILY.json`
- `family/LEARNING_DECISION.json`
- `family/closed/FINDING-005/`
- `results/HUMAN_SUMMARY.md`

## Residual intake (unmaterialized)

1. (closed earlier, other family) Telegram rec-bid overlay call site — ROOT-001 `closed_fixed`
2. (closed earlier, other family) `promo_state_service.py` — get_campaign_balance failure still `redis.set` with `pool_usable=false` — FINDING-002 + HC-001 `closed_fixed`
3. (closed earlier, false positive) `promo_ledger.py` — 90-day lookback drops campaign remaining — FINDING-003 `closed_false_positive`
4. (closed earlier, other family) `promo_accounting.py` — FEFO applies spend to expired leftover first — FINDING-004 + HC-FINDING-004-STALE-TEST `closed_fixed`
5. (closed this episode) campaign leftover fraction uses `budget_after/total` so M collapses — FINDING-005 `closed_fixed`
6. journal only bot `WBAutoBudgetTopUp`; manual WB promo deposits invisible

## Owner handoff

Worktree remains uncommitted. Review the diff and decide whether to commit.

NEXT_ACTION:

```text
/opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
```

SOFT:

```text
/opsx-bug-debt-board case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
```
