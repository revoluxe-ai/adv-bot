# Closure evidence: FINDING-004

```text
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-004
SIBLING_FINDING_ID: HC-FINDING-004-STALE-TEST
BUG_FAMILY_ID: BFAM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/FEFO-SPEND-SKIP-EXPIRED
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/FEFO-SPEND-SKIP-EXPIRED
FINDING_STATUS: closed_fixed
HC_FINDING_004_STALE_TEST_DISPOSITION: closed_fixed
EPISODE_TERMINAL: FIXED
CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A
FAMILY_STATUS: CLOSED_FIXED_VERIFIED
CLOSURE_STATUS: CLOSED_FIXED_VERIFIED
CASE_STATUS: OPEN_RESIDUAL_INTAKE
LEAVE_OPEN_REASON: partial_residual
RESIDUAL_INTAKE_ITEMS: 5, 6
MISSION_COMPLETE: no
CONTROL_MODEL: USER_REVIEWS_UNCOMMITTED_WORKTREE
EXECUTION_MODE: CONTROLLED_LIVE_UNCOMMITTED
COMMIT_CREATED: NO
WORKTREE_STATUS: UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
USER_ACTION_REQUIRED: REVIEW_DIFF_AND_DECIDE_COMMIT
CLOSED_AT: 2026-09-07T18:54:00Z
WORKER_ID: CLOSURE_OPERATOR
WORKER_EXECUTION_ID: WEX/CLOSURE_OPERATOR/50390aa9e9
ORCHESTRATION_ID: ORCH/sup-promo-t09-d09
CHECKPOINT_GENERATION: 61
```

## Hard gates

- HARD_BLOCK_READY / same-invariant candidate gate: PASS. `findings/HC-FINDING-004-STALE-TEST.md` STATUS is `materialized` at fan-in (not `open_candidate`); branch `INTEGRATED`. This hop terminates it as `closed_fixed`. Scan of `findings/` for `STATUS ∈ {open_candidate, OPEN_CANDIDATE}`: none. `OPEN_SAME_INVARIANT_CANDIDATES=NONE`.
- Episode FANIN gate: PASS. `results/FANIN.md` STATUS=`FANIN_READY`, `BLOCKING_FINDINGS=[]`, `CLOSURE_READINESS=READY_FOR_CLOSURE`, `OPEN_SAME_INVARIANT_CANDIDATES=NONE`.
- Root + sibling fix/green: PASS. FINDING-004 production skip-expired `GREEN_CONFIRMED` (`results/GREEN-FINDING-004.md`, `results/FIX-FINDING-004.md`). HC-FINDING-004-STALE-TEST assertion 200→150 `GREEN_CONFIRMED` + INTEGRATED (`results/GREEN-HC-FINDING-004-STALE-TEST.md`). Not FALSE_POSITIVE. Not OUT_OF_SCOPE.
- Learning gate: PASS. `runtime.learning_decision.evaluate_closure_learning_gate` → PASS on `family/LEARNING_DECISION.json`. `LEARNING_STAGE_INVOKED=true`, `LEARNING_VERDICT=LOCAL_CASE_NOTE_ONLY`, `LEARNING_STATUS=COMPLETE`, `PROMOTION_DECISION=RESOLVED_NO_PROMOTE`. Closure-allowed without promotion.

## What closed

FINDING-004 is `closed_fixed` / `EPISODE_TERMINAL=FIXED` / `CLASSIFICATION=IMPLEMENTATION_BUG` / `ROUTE_A`. HC-FINDING-004-STALE-TEST (SAME_INVARIANT sibling, INTEGRATED) is `closed_fixed` / `EPISODE_TERMINAL=FIXED` in the same family. Family `BFAM/.../FEFO-SPEND-SKIP-EXPIRED` is `CLOSED_FIXED_VERIFIED`.

Invariant: `apply_spend_fefo` must not apply spend to expired leftover before live leftover; expired 300 + live 200 + spend 50 must yield remaining 150. Production spend loop now `continue`s when `is_expired`. Sibling test assertion updated 200→150.

## What did not close

The CASE stays open (`OPEN_RESIDUAL_INTAKE` / `partial_residual`). INTAKE-001 residual items 5 and 6 remain unmaterialized. FINDING-005 / FINDING-006 were not created. `MISSION_COMPLETE: no`.

ROOT-001 remains `closed_fixed`. FINDING-002 and HC-001 remain `closed_fixed`. FINDING-003 remains `closed_false_positive`. This hop did not reopen them and did not overwrite `family/closed/FINDING-002/` or `family/closed/ROOT-001/`.

## Closure operator did not

Change production code, tests, OpenSpec, `results/FANIN.md`, or `family/LEARNING_DECISION.json`. Did not git commit, push, or deploy. Did not start intake items 5–6. Did not allocate FINDING-005 / FINDING-006. Did not paste `mode=resume-family-fanout`.

## Evidence paths

- `results/RED-FINDING-004.md`
- `results/FIX-FINDING-004.md`
- `results/GREEN-FINDING-004.md`
- `results/RED-HC-FINDING-004-STALE-TEST.md`
- `results/FIX-HC-FINDING-004-STALE-TEST.md`
- `results/GREEN-HC-FINDING-004-STALE-TEST.md`
- `results/FANIN.md`
- `family/FAMILY.json`
- `family/LEARNING_DECISION.json`
- `family/closed/FINDING-004/`
- `results/HUMAN_SUMMARY.md`

## Residual intake (unmaterialized)

1. (closed earlier, other family) Telegram rec-bid overlay call site — ROOT-001 `closed_fixed`
2. (closed earlier, other family) `promo_state_service.py` — get_campaign_balance failure still `redis.set` with `pool_usable=false` — FINDING-002 + HC-001 `closed_fixed`
3. (closed earlier, false positive) `promo_ledger.py` — 90-day lookback drops campaign remaining — FINDING-003 `closed_false_positive`
4. (closed this episode) `promo_accounting.py` — FEFO applies spend to expired leftover first — FINDING-004 + HC-FINDING-004-STALE-TEST `closed_fixed`
5. campaign leftover fraction uses `budget_after/total` so M collapses
6. journal only bot `WBAutoBudgetTopUp`; manual WB promo deposits invisible

## Owner handoff

Worktree remains uncommitted. Review the diff and decide whether to commit.

NEXT_ACTION:

```text
/opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
```

SOFT:

```text
/opsx-bug-debt-board case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z ok
```
