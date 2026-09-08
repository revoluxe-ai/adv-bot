# Closure evidence: FINDING-003

```text
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-003
BUG_FAMILY_ID: (none; CALL_CLOSE_FAMILY=false)
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-003/LEFTOVER-NO-90D-CUTOFF
FINDING_STATUS: closed_false_positive
FINDING_TERMINAL_KIND: CLOSED_FALSE_POSITIVE
EPISODE_TERMINAL: FALSE_POSITIVE
EPISODE_TERMINAL_MAPPED: REJECTED
CLASSIFICATION: FALSE_POSITIVE
CHOSEN_ROUTE: ROUTE_C
CURRENT_ROUTE_STATE: CLOSED_NO_IMPLEMENTATION
CLOSURE_STATUS: CLOSED_FALSE_POSITIVE
CASE_STATUS: OPEN_RESIDUAL_INTAKE
LEAVE_OPEN_REASON: partial_residual
RESIDUAL_INTAKE_ITEMS: 4, 5, 6
MISSION_COMPLETE: no
CONTROL_MODEL: USER_REVIEWS_UNCOMMITTED_WORKTREE
EXECUTION_MODE: CONTROLLED_LIVE_UNCOMMITTED
COMMIT_CREATED: NO
WORKTREE_STATUS: UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
USER_ACTION_REQUIRED: REVIEW_DIFF_AND_DECIDE_COMMIT
CLOSED_AT: 2026-09-07T16:10:12Z
WORKER_ID: CLOSURE_OPERATOR
WORKER_EXECUTION_ID: WEX/CLOSURE_OPERATOR/99a510bc28
ORCHESTRATION_ID: ORCH/sup-promo-t07-d07
CHECKPOINT_GENERATION: 41
```

## Hard gates

- HARD_BLOCK_READY / same-invariant candidate gate: PASS. Hunt `WEX/BOUNDED_HUNTER/b69d090049` is `HUNT_RESULT=CLEAR` with `CANDIDATES=[]`. Scan of `findings/` for `STATUS ∈ {open_candidate, OPEN_CANDIDATE}`: none. `OPEN_SAME_INVARIANT_CANDIDATES=NONE`.
- Episode FANIN gate: PASS. `results/FANIN.md` STATUS=`FANIN_READY`, `BLOCKING_FINDINGS=NONE`, `CLOSURE_READINESS=READY_FOR_CLOSURE`. Route C: no RED, no GREEN, no Owner production GO.
- Learning gate: PASS. `runtime.learning_decision.evaluate_closure_learning_gate` → PASS on `family/LEARNING_DECISION.json`. `LEARNING_VERDICT=LOCAL_CASE_NOTE_ONLY`, `LEARNING_STATUS=COMPLETE`, `PROMOTION_DECISION=RESOLVED_NO_PROMOTE`. Closure-allowed without promotion.

## What closed

FINDING-003 is `closed_false_positive` / `FINDING_TERMINAL_KIND=CLOSED_FALSE_POSITIVE` / `EPISODE_TERMINAL=FALSE_POSITIVE` (mapped episode kind `REJECTED`). Classification `FALSE_POSITIVE`, `CHOSEN_ROUTE=ROUTE_C`, `CLOSED_NO_IMPLEMENTATION`.

Reported defect: `promo_ledger.py` 90-day lookback drops campaign remaining into a false AND-stop. Authoritative classifier: leftover-usable `load_campaign_ledgers` does not pass `cutoff=`. `PROMO_LOOKBACK_DAYS=90` is UPD ingest recovery in `PromoStateService._resolve_upd_from_date`, not a leftover remaining filter. Living leftover older than 90d remains usable. No production defect on this finding. No implementation. No GREEN.

## What did not close

The CASE stays open (`OPEN_RESIDUAL_INTAKE` / `partial_residual`). INTAKE-001 residual items 4, 5, 6 remain unmaterialized. FINDING-004..006 were not created. `MISSION_COMPLETE: no`.

ROOT-001 remains `closed_fixed`. FINDING-002 and HC-001 remain `closed_fixed`. This hop did not reopen them and did not write `results/OWNER-CLOSURE-ROOT-001.md` or `results/OWNER-CLOSURE-FINDING-002.md`.

## Closure operator did not

Change production code, tests, OpenSpec, `results/FANIN.md`, `family/LEARNING_DECISION.json`, or `intakes/`. Did not git commit, push, or deploy. Did not start intake items 4–6. Did not allocate FINDING-004..006. Did not run GREEN. Did not call close_family.

## Evidence paths

- `results/PROOF-CLASSIFIER-WEXe1b15347b7.md`
- `results/PROOF-HUNT-BOUNDED-HUNTER-FINDING-003.md`
- `results/FANIN.md`
- `family/LEARNING_DECISION.json`
- `results/LEARNING_REPORT.md`
- `results/HUMAN_SUMMARY.md`

## Residual intake (unmaterialized)

1. (closed earlier) Telegram rec-bid overlay call site — ROOT-001 `closed_fixed`
2. (closed earlier) `promo_state_service.py` — get_campaign_balance failure still `redis.set` with `pool_usable=false` — FINDING-002 + HC-001 `closed_fixed`
3. (closed this episode, false positive) `promo_ledger.py` — 90-day lookback drops campaign remaining — FINDING-003 `closed_false_positive`
4. `promo_accounting.py` — FEFO applies spend to expired tranches first
5. campaign leftover fraction uses `budget_after/total` so M collapses
6. journal only bot `WBAutoBudgetTopUp`; manual WB promo deposits invisible

## Owner handoff

Worktree remains uncommitted. Review the diff and decide whether to commit. This hop added no production diff.

NEXT_ACTION:

```text
/opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
```
