# Closure evidence: FINDING-002

```text
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-002
SIBLING_FINDING_ID: HC-001
BUG_FAMILY_ID: BFAM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-002/PROMO-POOL-FAIL-NO-FALSE-EMPTY
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-002/PROMO-POOL-FAIL-NO-FALSE-EMPTY
FINDING_STATUS: closed_fixed
HC001_DISPOSITION: closed_fixed
EPISODE_TERMINAL: FIXED
FAMILY_STATUS: CLOSED_FIXED_VERIFIED
CLOSURE_STATUS: CLOSED_FIXED_VERIFIED
CASE_STATUS: OPEN_RESIDUAL_INTAKE
LEAVE_OPEN_REASON: partial_residual
RESIDUAL_INTAKE_ITEMS: 3, 4, 5, 6
MISSION_COMPLETE: no
CONTROL_MODEL: USER_REVIEWS_UNCOMMITTED_WORKTREE
EXECUTION_MODE: CONTROLLED_LIVE_UNCOMMITTED
COMMIT_CREATED: NO
WORKTREE_STATUS: UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
USER_ACTION_REQUIRED: REVIEW_DIFF_AND_DECIDE_COMMIT
CLOSED_AT: 2026-09-07T15:10:00Z
WORKER_ID: CLOSURE_OPERATOR
WORKER_EXECUTION_ID: WEX/CLOSURE_OPERATOR/b7c84d04a3
ORCHESTRATION_ID: ORCH/sup-promo-t06-d06
CHECKPOINT_GENERATION: 34
```

## Hard gates

- HARD_BLOCK_READY / same-invariant candidate gate: PASS. `findings/HC-001.md` STATUS is `materialized` at fan-in (not `open_candidate`); this hop terminates it as `closed_fixed`. `OPEN_SAME_INVARIANT_CANDIDATES=NONE`. Scan of `findings/` for `STATUS ∈ {open_candidate, OPEN_CANDIDATE}`: none.
- Episode FANIN gate: PASS. `results/FANIN.md` STATUS=`FANIN_READY`, `BLOCKING_FINDINGS=NONE`, `CLOSURE_READINESS=READY_FOR_CLOSURE`.
- Family fan-in gate: PASS. `results/FAMILY-FANIN.md` `READY_FOR_FAMILY_CLOSURE`. Integration `PASS`. Family green `FAMILY_GREEN_STATUS: PASS`.
- Root + sibling fix/green: PASS. FINDING-002 Exception path `GREEN_CONFIRMED` (`results/GREEN-FINDING-002.md`, `results/FIX-FINDING-002.md`). HC-001 None path `GREEN_CONFIRMED` + INTEGRATED (`results/GREEN-HC-001.md`, `results/FIX-HC-001.md`).
- Learning gate: PASS. `runtime.learning_decision.evaluate_closure_learning_gate` → PASS. `LEARNING_VERDICT=LOCAL_CASE_NOTE_ONLY`, `LEARNING_STATUS=COMPLETE`, `PROMOTION_DECISION=RESOLVED_NO_PROMOTE`. Closure-allowed without promotion.

## What closed

FINDING-002 is `closed_fixed` / `EPISODE_TERMINAL=FIXED`. HC-001 (SAME_INVARIANT sibling, None-return) is `closed_fixed` / `EPISODE_TERMINAL=FIXED` in the same family. Family `BFAM/.../PROMO-POOL-FAIL-NO-FALSE-EMPTY` is `CLOSED_FIXED_VERIFIED`.

Invariant: on `get_campaign_balance` failure, do not `redis.set` a fresh `pool_usable=false` snapshot; miss/stale → conservative M=1. Exception skip (FINDING-002) + None identity gate (HC-001).

## What did not close

The CASE stays open (`OPEN_RESIDUAL_INTAKE` / `partial_residual`). INTAKE-001 residual items 3, 4, 5, 6 remain unmaterialized. FINDING-003..006 were not created. `MISSION_COMPLETE: no`.

ROOT-001 remains `closed_fixed` in a different overlay family. This hop did not reopen it and did not write `results/OWNER-CLOSURE-ROOT-001.md` or `family/closed/ROOT-001/**`.

## Closure operator did not

Change production code, tests, OpenSpec, `results/FANIN.md`, or `family/LEARNING_DECISION.json`. Did not git commit, push, or deploy. Did not start intake items 3–6. Did not allocate FINDING-003..006.

## Evidence paths

- `results/RED-FINDING-002.md`
- `results/FIX-FINDING-002.md`
- `results/GREEN-FINDING-002.md`
- `results/RED-HC-001.md`
- `results/FIX-HC-001.md`
- `results/GREEN-HC-001.md`
- `results/FANIN.md`
- `results/FAMILY-FANIN.md`
- `family/FAMILY.json`
- `family/LEARNING_DECISION.json`
- `results/HUMAN_SUMMARY.md`

## Residual intake (unmaterialized)

1. (closed earlier, other family) Telegram rec-bid overlay call site — ROOT-001
2. (closed this episode) `promo_state_service.py` — get_campaign_balance failure still `redis.set` with `pool_usable=false` — FINDING-002 + HC-001
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
