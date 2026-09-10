# FANIN — BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z / ROOT-001

```text
STATUS: FANIN_READY
CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
ROOT_FINDING_ID: ROOT-001
ASSEMBLED_AT: 2026-09-07T13:21:08Z
ASSEMBLER: FAN_IN_ASSEMBLER
WORKER_EXECUTION_ID: WEX/FAN_IN_ASSEMBLER/5ac9cb6bf9
ORCHESTRATION_ID: ORCH/BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z/FANOUT-1
EXECUTION_MODE: CONTROLLED_LIVE_UNCOMMITTED
MAPS_TO: /opsx-materialize-bug-queue mode=fanin_assemble
HARD_BLOCK_READY: NO
BLOCKING_FINDINGS: NONE
CLOSURE_READINESS: READY_FOR_CLOSURE
```

Episode FANIN for ROOT-001 leftover-90d AND-stop. Hunt `CLEAR`.
`OPEN_SAME_INVARIANT_CANDIDATES=[]`. FINDING-H2..H6 are existing-on-case
`NEW_ROOT_CAUSE` / `different_invariant` backlog and do **not** block ROOT
family `FANIN_READY`. Family assemble (`results/FAMILY-FANIN.md`) is
`READY_FOR_FAMILY_CLOSURE`. `LEARNING_READY ≠ FANIN_READY`.

## ROOT_BUG

`load_campaign_ledgers` applied `PROMO_LOOKBACK_DAYS` (90d) cutoff to leftover
success-tranches and spend, so a non-expired leftover with `remaining>0` and
`created_at` older than 90d dropped out of the campaign ledger. Overlay then
AND-stopped (`campaign_usable=false` / conservative M=1) while campaign leftover
remained, including when the common pool was empty.

## ROOT_CAUSE_PATTERN

Lookback window used as leftover-usable filter (`created_at >= now-90d` on
allocation/spend load) instead of leftover remaining + `expires_at`. Cutoff
false-zeroed `campaign_usable` and AND-stopped overlay for a living leftover.

## ERROR_CLASS

`PROMO_LEFTOVER_LOOKBACK_AND_STOP` — `PROMO_LOOKBACK_DAYS` cutoff in
`load_campaign_ledgers` false-stops overlay while leftover `remaining>0` and
not expired.

## ROOT_INVARIANT

```text
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z/4ae535b7
INVARIANT: A leftover success-tranche with remaining>0 and not expired keeps
  campaign_usable / overlay usable true even when created_at is older than
  PROMO_LOOKBACK_DAYS and pool=0. The 90d lookback must not AND-stop a living leftover.
```

## SIBLING_VARIANTS

none for leftover-90d.

Bounded hunt (`results/HUNT-ROOT-001.md`, `results/HUNT-CANDIDATES.json`)
returned `HUNT_RESULT: CLEAR`, `CANDIDATES: []`. No `findings/HC-*`. No
`RELATION_TO_ROOT_CANDIDATE=SAME_INVARIANT_FINDING` open candidates.

FINDING-H2..H6 are **not** leftover-90d sibling variants; listed under
`REMAINING_EXCEPTIONS` as `different_invariant` backlog.

## FIX_PATTERNS

1. In `load_campaign_ledgers`, load leftover success-tranches and persisted
   spend **without** `PROMO_LOOKBACK_DAYS` cutoff so leftover `remaining>0`
   and not expired keeps `campaign_usable=true` outside 90d when `pool=0`.
2. Keep allocation and spend windows aligned (both uncapped on PG load) so
   remaining is not overstated by dropping spend while keeping allocation.
3. Leave UPD ingest lookback (`PromoStateService._UPD_LOOKBACK_DAYS`) unchanged.
4. Do not start FINDING-H2..H6 on this hop (`MAX_ACTIVE_FINDINGS=1`).

Production path: `app/modules/auto_budget_manager/promo_ledger.py` (uncommitted).
PRODUCTION_HASH_BEFORE: `sha256:56a47501eeeeac63876b1e805b04bacb57e7e2e39547d5c2838066da40e74575`
PRODUCTION_HASH_AFTER: `sha256:ddb653b68b87befc63f62154558fde66b732623a330f3801ecff3112c3917598`
Unchanged: `promo_accounting.py` `sha256:271f404d1569658207038cd45092e5fa04a98efd3a6dd67b5702aae214d24f4f`;
`promo_overlay.py` `sha256:adace8040975ab7476396137cb9e71699ff770af648f8d060916add4054a70bc`.

## REGRESSION_TEST_PATTERN

Frozen leftover-older-than-lookback unit node (RED ↔ GREEN hash match):

- `tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero`

TEST_CONTENT_SHA256: `ec18863bc09e7075787173b86c854ec6019eac58394d746904b7494c59eeb72a`
TEST_CONTENT_SHA256_MATCH_RED: YES
NON_WEAKEN_DELTA: none
REGRESSION_STATUS: GREEN_CONFIRMED leftover-older-than-lookback

Targeted regressions: leftover success-tranche `remaining>0`, not expired,
`created_at` older than 90d, `pool=0` keeps `campaign_usable=true` and overlay
usable=true (no 90d AND-stop).

## PREVENTION_RULE_CANDIDATE

`PROMO_LOOKBACK_DAYS` must not drop a non-expired leftover success-tranche with
`remaining>0` from `load_campaign_ledgers`. Overlay usable / `campaign_usable`
must follow leftover remaining + expiry, not `created_at` lookback. UPD ingest
recovery window is a different concern and must not be reused as leftover-usable
AND-stop.

## REUSABLE_CHECK_CANDIDATE

Scan production callers of `load_success_tranches` / `load_spend_rows` that pass
`cutoff=` on the leftover-usable overlay path (`load_campaign_ledgers` /
`PromoStateService.refresh`). Flag any `created_at >= now-PROMO_LOOKBACK_DAYS`
filter that can AND-stop overlay while leftover `remaining>0` and not expired.

## REMAINING_EXCEPTIONS

FINDING-H2..H6 backlog `different_invariant` on this case; sequential
`MAX_ACTIVE_FINDINGS=1` after ROOT close. Not SAME_INVARIANT. Do not block
ROOT closure.

```text
FINDING-H2: NEW_ROOT_CAUSE / different_invariant / backlog
  campaign f denominator (budget_after/wallet vs top-up unit)
FINDING-H3: NEW_ROOT_CAUSE / different_invariant / backlog
  one-tick overlay lag after pool and leftover exhausted
FINDING-H4: NEW_ROOT_CAUSE / different_invariant / backlog
  plan_fact_stats persists overlay.plan instead of raw get_plan_data
FINDING-H5: NEW_ROOT_CAUSE / different_invariant / backlog
  keyword GOOD/BAD resolve wipes overlay CPO via AdvSetting/CH
FINDING-H6: NEW_ROOT_CAUSE / different_invariant / backlog
  pick_cashback_for_topup prefers expired package over live FEFO
```

Uncommitted worktree: Owner must review before commit. Not a SAME_INVARIANT
block.

## BRANCH_SUMMARY

no SAME_INVARIANT branches.

| FINDING_ID | ROLE | EPISODE_TERMINAL | RED | FIX | GREEN | OWNER_PRODUCTION_GO | NOTES |
|---|---|---|---|---|---|---|---|
| ROOT-001 | ROOT | (empty; not closed; FANIN_READY) | results/RED-ROOT-001.md | results/FIX-ROOT-001.md | results/GREEN-ROOT-001.md | results/OWNER-GO-ROOT-001.md | GREEN_CONFIRMED leftover-older-than-lookback; hunt CLEAR |

BRANCH_REGISTRY (LEDGER snapshot, read-only): ROOT-001 DEPTH=0 EPISODE_TERMINAL=no OWNER_PRODUCTION_GO=yes.
No SAME_INVARIANT child rows. FINDING-H2..H6 are backlog on this case, not
started branches of this invariant.

```text
HUNT_PASSES_EXECUTED: 1 (hunt artifacts; LEDGER snapshot still 0)
MAX_DEPTH_SEEN: 0
ACTIVE_BRANCH_COUNT: 1 (ROOT-001 claimed, not closed)
MAX_HUNT_PASSES: 3
MAX_DEPTH_FROM_ROOT: 3
MAX_ACTIVE_BRANCHES: 3
MAX_ACTIVE_FINDINGS: 1
```

## HUNT_SUMMARY

```text
HUNT_RESULT: CLEAR
HUNT_PASSES_EXECUTED: 1
MAX_HUNT_PASSES: 3
CANDIDATES: []
OPEN_SAME_INVARIANT_CANDIDATES: 0
HUNT_EVIDENCE: results/HUNT-ROOT-001.md
HUNT_CANDIDATES: results/HUNT-CANDIDATES.json
FAMILY_RELATION: family/RELATION.json
```

## SAME_INVARIANT_SCAN

```text
findings/HC-*: none
HUNT CANDIDATES: []
STATUS open_candidate / OPEN_CANDIDATE: none
RELATION_TO_ROOT_CANDIDATE=SAME_INVARIANT_FINDING: none
FINDING-H2..H6: EXISTING_ON_CASE NEW_ROOT_CAUSE / different_invariant / backlog
  NOT SAME_INVARIANT OPEN_CANDIDATE; do not block ROOT FANIN_READY
HARD_BLOCK_READY: NO
BLOCKING_FINDINGS: NONE
NO_OPEN_SAME_INVARIANT_CANDIDATES: true
```

## CLOSURE_READINESS

```text
CLOSURE_READINESS: READY_FOR_CLOSURE
BLOCKS_ROOT_CLOSURE: false
BLOCKING_FINDINGS: NONE
NO_OPEN_SAME_INVARIANT_CANDIDATES: true
LEARNING_READY: NOT_CLAIMED_BY_FANIN
LEARNING_STARTED: no
CLOSURE_STARTED: no
MISSION_COMPLETE: no
FINDING_TERMINAL: no
```

`BLOCKS_ROOT_CLOSURE=false` applies because there are **no** SAME_INVARIANT
open candidates. FINDING-H2..H6 remain sequential backlog after ROOT close;
they do not set `BLOCKS_ROOT_CLOSURE`.

```text
LESSON_CANDIDATE_ONLY until Owner FINAL after FANIN_READY
CLASS_STATUS: OPEN
CLASS_LEVEL_GO_WRITE: FORBIDDEN until Owner FINAL
```

`LEARNING_READY` is not `FANIN_READY`. Do not start FINDING-H2..H6 until ROOT
is closed (`MAX_ACTIVE_FINDINGS=1`).

## REGRESSION_STATUS

```text
REGRESSION_STATUS: GREEN_CONFIRMED leftover-older-than-lookback
ROOT-001: RED_CONFIRMED -> FIXED_UNCOMMITTED -> GREEN_CONFIRMED
PYTEST (frozen node): PASSED exit 0 (GREEN-ROOT-001.md)
ADJACENT: tests/unit/auto_budget_manager/test_promo_ledger.py 4 passed
TEST_CONTENT_SHA256_MATCH_RED: YES
NON_WEAKEN_DELTA: none
EPISODE: FANIN_READY
```

## LIMITS_CHECK

```text
LIMITS_CHECK: PASS
HUNT_PASSES_EXECUTED: 1 <= MAX_HUNT_PASSES: 3
MAX_DEPTH_SEEN: 0 <= MAX_DEPTH_FROM_ROOT: 3
ACTIVE_BRANCH_COUNT: 1 <= MAX_ACTIVE_BRANCHES: 3
DEPTH: 0
MAX_ACTIVE_FINDINGS: 1 (H2-H6 RED not started)
```

## CHECKS

```text
1_FIXED_HAVE_RED_GREEN_GO: PASS
   ROOT-001 has RED + FIX + GREEN + OWNER-GO-ROOT-001. Frozen TEST_ID linked.
2_NO_WEAKEN: PASS
   TEST_CONTENT_SHA256 identical RED->GREEN; NON_WEAKEN_DELTA=none.
3_NO_DOUBLE_FIX: PASS
   Single IMPLEMENTATION_EXECUTOR hop on promo_ledger.py. H2-H6 not implemented.
4_NO_CONFLICTING_PRODUCTION_DIFFS: PASS
   Sole production file for this episode: promo_ledger.py; one before/after
   hash pair. promo_accounting.py and promo_overlay.py unchanged.
5_ONE_ROOT_INVARIANT_OR_EXPLICIT_OUTEPISODE: PASS
   One leftover-90d invariant. H2-H6 explicit different_invariant
   out-of-episode backlog on this case. No SAME_INVARIANT branches.
6_LIMITS_NOT_EXCEEDED: PASS
   Hunt passes / depth / active branches within limits.
```

## NEXT_ACTION

ROOT episode assemble complete. Closure of ROOT-001 is unblocked.
FINDING-H2..H6 remain sequential `MAX_ACTIVE_FINDINGS=1` after ROOT close.
