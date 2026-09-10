# Closure evidence: ROOT-001

```text
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: ROOT-001
BUG_FAMILY_ID: BFAM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/ROOT-001/PROMO-OVERLAY-REC-BID
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/ROOT-001/PROMO-OVERLAY-REC-BID
FINDING_STATUS: closed_fixed
EPISODE_TERMINAL: FIXED
FAMILY_STATUS: CLOSED_FIXED_VERIFIED
CLOSURE_STATUS: CLOSED_FIXED_VERIFIED
CASE_STATUS: OPEN_RESIDUAL_INTAKE
LEAVE_OPEN_REASON: partial_residual
MISSION_COMPLETE: no
CONTROL_MODEL: USER_REVIEWS_UNCOMMITTED_WORKTREE
EXECUTION_MODE: CONTROLLED_LIVE_UNCOMMITTED
COMMIT_CREATED: NO
WORKTREE_STATUS: UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
USER_ACTION_REQUIRED: REVIEW_DIFF_AND_DECIDE_COMMIT
CLOSED_AT: 2026-09-07T11:52:00Z
WORKER_ID: CLOSURE_OPERATOR
WORKER_EXECUTION_ID: WEX/CLOSURE_OPERATOR/834feb7f6c
ORCHESTRATION_ID: ORCH/sup-promo-t04-d04
```

## Hard gates

- Same-invariant candidate gate: PASS. Bounded hunt is `CLEAR`. `findings/` contains only `ROOT-001.md`. `OPEN_SAME_INVARIANT_CANDIDATES=[]`. No `HUNT-*` findings. HARD_BLOCK_READY does not fire.
- Family fan-in gate: PASS. `results/FAMILY-FANIN.md` is `READY_FOR_FAMILY_CLOSURE`. Integration `PASS_NO_BRANCH_INTEGRATION_REQUIRED`. Blocking findings: none.
- Root fix and green gate: PASS. `results/FIX-ROOT-001.md` and `results/GREEN-ROOT-001.md` (`GREEN_CONFIRMED`). Frozen Telegram rec-bid `plan_context` node uses overlay target/max pay when live `promo_fraction > 0`.
- Learning gate: PASS. `family/LEARNING_DECISION.json` records `LEARNING_STAGE_INVOKED=true`, `LEARNING_STATUS=COMPLETE`, `LEARNING_VERDICT=EXISTING_POLICY_COMPLIANCE_FAILURE`, `PROMOTION_DECISION=RESOLVED_NO_PROMOTE`. Closure-allowed without promotion.

## What closed

Finding ROOT-001 is `closed_fixed` / `CLOSED_FIXED_VERIFIED` (`EPISODE_TERMINAL=FIXED`). Overlay family `BFAM/.../PROMO-OVERLAY-REC-BID` is `CLOSED_FIXED_VERIFIED`.

## What did not close

The CASE stays open (`OPEN_RESIDUAL_INTAKE` / `partial_residual`). INTAKE-001 residual items 2, 3, 4, 5, 6 remain unmaterialized. FINDING-002..006 were not created. `MISSION_COMPLETE: no`.

## Closure operator did not

Change production code, tests, OpenSpec, `results/FANIN.md`, or `family/LEARNING_DECISION.json`. Did not git commit, push, or deploy.

## Evidence paths

- `results/RED-ROOT-001.md`
- `results/FIX-ROOT-001.md`
- `results/GREEN-ROOT-001.md`
- `results/PROOF-HUNT-BOUNDED-HUNTER-001.md`
- `results/FAMILY-FANIN.md`
- `family/FAMILY.json`
- `family/LEARNING_DECISION.json`
- `results/HUMAN_SUMMARY.md`

## Residual intake (unmaterialized)

1. (closed this episode) Telegram rec-bid overlay call site — ROOT-001
2. `promo_state_service.py` — get_campaign_balance failure still `redis.set` with `pool_usable=false`
3. `promo_ledger.py` — 90-day lookback drops campaign remaining
4. `promo_accounting.py` — FEFO applies spend to expired tranches first
5. campaign leftover fraction uses `budget_after/total` so M collapses
6. journal only bot `WBAutoBudgetTopUp`; manual WB promo deposits invisible

## Owner handoff

Worktree remains uncommitted. Review the diff and decide whether to commit.

NEXT_ACTION:

```text
/opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
```
