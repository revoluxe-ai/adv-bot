# FANIN - BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z / FINDING-006

```text
STATUS: FANIN_READY
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
ROOT_FINDING_ID: FINDING-006
ASSEMBLED_AT: 2026-09-07T20:55:00Z
ASSEMBLER: FAN_IN_ASSEMBLER
WORKER_EXECUTION_ID: WEX/FAN_IN_ASSEMBLER/601562bda0
ORCHESTRATION_ID: ORCH/sup-promo-t11-d11
EXECUTION_MODE: CONTROLLED_LIVE_UNCOMMITTED
MAPS_TO: /opsx-materialize-bug-queue mode=fanin_assemble
HARD_BLOCK_READY: false
BLOCKING_FINDINGS: []
OPEN_SAME_INVARIANT_CANDIDATES: NONE
BLOCKS_ROOT_CLOSURE: false
CLOSURE_READINESS: READY_FOR_CLOSURE
CHECKPOINT_GENERATION: 77
PACKET_GENERATION: 1
CLASSIFICATION: FALSE_POSITIVE
CHOSEN_ROUTE: ROUTE_C
LEARNING_READY: NOT_CLAIMED
MISSION_COMPLETE: no
FINDING_TERMINAL: no
FINDING_TERMINAL_KIND: CLOSED_FALSE_POSITIVE
CASE_STATUS: OPEN
RESIDUAL_INTAKE_ITEMS: []
LEAVE_OPEN_REASON:
DO_NOT_CREATE_FINDING_007: true
DO_NOT_REOPEN_ROOT_001: true
DO_NOT_REOPEN_FINDING_002: true
DO_NOT_REOPEN_HC_001: true
DO_NOT_REOPEN_FINDING_003: true
DO_NOT_REOPEN_FINDING_004: true
DO_NOT_REOPEN_HC_FINDING_004_STALE_TEST: true
DO_NOT_REOPEN_FINDING_005: true
SUPERSEDES_WEX: WEX/FAN_IN_ASSEMBLER/665d4ffc8b
HUNT_RESULT: CLEAR
CANDIDATES: []
```

Episode FANIN for FINDING-006 (INTAKE-001 MEDIUM item 6) only.
Classification is FALSE_POSITIVE / ROUTE_C. No implementation. No RED.
No GREEN. No production diff. Hunt `WEX/BOUNDED_HUNTER/14c710e724` is
`HUNT_RESULT=CLEAR` with `CANDIDATES=[]`. No HC sibling. Residual intake
is empty (item 6 was last). FINDING-006 is not closed
(`FINDING_TERMINAL=no` until CLOSURE_OPERATOR).

This file supersedes the prior episode FANIN from
`WEX/FAN_IN_ASSEMBLER/665d4ffc8b` (FINDING-005 / FANIN_READY). FINDING-005
family stays closed_fixed and is not reopened. Prior closed families stay
closed.

HARD_BLOCK_READY does **not** fire. Hunt residual scan (verify, not invented):

```text
HUNT_RESULT: CLEAR
CANDIDATES: []
HUNT_PACKET: team/packets/WEX_BOUNDED_HUNTER_14c710e724.out.json
HUNT_PROOF: results/PROOF-HUNT-BOUNDED-HUNTER-FINDING-006.md
findings/HC-* for FINDING-006: none created
findings/HC-001.md
  STATUS: closed_fixed
  RELATION_TO_ROOT_CANDIDATE: SAME_INVARIANT_FINDING (FINDING-002 family)
  OPEN_CANDIDATE: NO
  OUT_OF_EPISODE: YES
findings/HC-FINDING-004-STALE-TEST.md
  STATUS: closed_fixed
  RELATION_TO_ROOT_CANDIDATE: SAME_INVARIANT_FINDING (FINDING-004 family)
  OPEN_CANDIDATE: NO
  OUT_OF_EPISODE: YES
LEDGER OPEN_SAME_INVARIANT_CANDIDATES: NONE
INDEX OPEN_CANDIDATES: 0 (read-only; this worker does not rewrite INDEX)
```

HARD_BLOCK_READY fires **only** when
`RELATION_TO_ROOT_CANDIDATE=SAME_INVARIANT_FINDING` **and**
`STATUS ∈ {open_candidate, OPEN_CANDIDATE}` **and** not disposed
`FALSE_POSITIVE` / `OUT_OF_SCOPE`. No such candidate exists for this episode.

```text
OPEN_SAME_INVARIANT_CANDIDATES: NONE
HARD_BLOCK_READY: false
BLOCKING_FINDINGS: []
BLOCKS_ROOT_CLOSURE: false
CLOSURE_READINESS: READY_FOR_CLOSURE
```

Case stays `OPEN` awaiting CLOSURE_OPERATOR. Residual intake is empty.
Do not create FINDING-007. Do not reopen ROOT-001, FINDING-002, HC-001,
FINDING-003, FINDING-004, HC-FINDING-004-STALE-TEST, or FINDING-005.
`LEARNING_READY ≠ FANIN_READY`; `LEARNING_READY=NOT_CLAIMED`.

## ROOT_BUG

Review restated the bot journal contract as a defect: WBAutoBudgetTopUp
records only bot auto-budget top-ups, so manual seller-portal promo
deposits are invisible in that table.

Classifier (`WEX/CLASSIFIER/30d9a4e237`) decided this is FALSE_POSITIVE /
ROUTE_C. WBAutoBudgetTopUp is the bot auto-budget journal by design.
Campaign remaining is FEFO on verified WBAutoBudgetTopUp allocations minus
UPD spend. Unused wallet promo stays on live WB cashbacks[] / pool_usable.
Manual seller-portal deposits are outside this journal SoT.

LOC_LINK: `app/modules/common_slaves/wildberries/models/wb_auto_budget_topup.py:36`

## ROOT_CAUSE_PATTERN

No production defect. The reported "journal-only-bot / manual deposits
invisible" effect is the documented table contract, not a missing persist
of seller-portal deposits.

## ERROR_CLASS

`FALSE_POSITIVE_JOURNAL_BOT_ONLY_NOT_MANUAL_DEPOSIT_LEDGER` — review treated
bot-only WBAutoBudgetTopUp as incomplete WB finance ledger.

## ROOT_INVARIANT

```text
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-006/JOURNAL-BOT-ONLY
INVARIANT: WBAutoBudgetTopUp is the bot auto-budget journal only. Campaign remaining uses verified bot allocations minus UPD spend. Unused wallet promo stays on live WB cashbacks. Manual seller-portal deposits are outside this journal SoT.
PRODUCTION_STATUS: contract confirmed FALSE_POSITIVE / ROUTE_C; no implementation
SIBLING_STATUS: none (HUNT_RESULT=CLEAR; CANDIDATES=[])
```

Not the ROOT-001 overlay invariant. Not the FINDING-002 / HC-001 pool-fail
invariant. Not the FINDING-003 90d leftover-cutoff (false-positive) report.
Not the FINDING-004 FEFO skip-expired invariant. Not the FINDING-005 leftover
fraction invariant. Sequential residual, different claim.

## SIBLING_VARIANTS

```text
NONE
HUNT_RESULT: CLEAR
CANDIDATES: []
NO_OPEN_SAME_INVARIANT_CANDIDATES: true
```

Hunt enumerated WBAutoBudgetTopUp constructor, both `_create_topup_entry`
callers, `load_success_tranches` / `load_campaign_ledgers`, campaign remaining
SoT, `resolve_promo_availability`, and Redis derived cache. Zero persist/load
of seller-portal deposits. Zero leftover/pool empty-as-journal-defect.
DUP-001 / DUP-002 / DUP-003 on the hunt proof are same-causal-path
observations of the known finding, not children. ADJ-001 / ADJ-002 are
adjacent unused-wallet / AND-stop observations, not SAME_INVARIANT
`open_candidate` residuals.

Not variants of this episode; not HARD_BLOCK; explicit out-of-episode:

- ROOT-001 Telegram rec-bid overlay (closed_fixed; do not reopen)
- FINDING-002 / HC-001 pool-fail false-empty Redis (closed_fixed; do not reopen)
- FINDING-003 90d leftover cutoff (closed_false_positive; do not reopen)
- FINDING-004 / HC-FINDING-004-STALE-TEST FEFO expired-spend (closed_fixed / INTEGRATED; do not reopen)
- FINDING-005 leftover fraction tranche.amount (closed_fixed; do not reopen)

## FIX_PATTERNS

NONE. Route C / CLOSED_NO_IMPLEMENTATION. No production write. No test write.

COMMIT_CREATED: NO (CONTROLLED_LIVE_UNCOMMITTED)

## REGRESSION_TEST_PATTERN

```text
REQUIRED_REGRESSION_TEST: not_applicable (FALSE_POSITIVE; no implementation)
RED_EVIDENCE_PATH:
GREEN_EVIDENCE_PATH:
FIX_EVIDENCE_PATH:
NON_WEAKEN_DELTA: none
GREEN_STATUS: N/A
CLASSIFIER_PROOF: results/PROOF-CLASSIFIER-WEX30d9a4e237.md
HUNT_PROOF: results/PROOF-HUNT-BOUNDED-HUNTER-FINDING-006.md
```

Journal SoT remains bot WBAutoBudgetTopUp. Unused wallet promo remains live
WB cashbacks[].

## PREVENTION_RULE_CANDIDATE

Do not treat WBAutoBudgetTopUp bot-only persistence as a missing seller-portal
deposit ledger. Manual deposits stay outside that journal. Unused wallet promo
is live WB cashbacks[] / pool_usable.

## REUSABLE_CHECK_CANDIDATE

Scan for persist/load of seller-portal / manual deposits into
WBAutoBudgetTopUp, or leftover/pool emptied because the journal lacks those
rows. Expected: none (bot `_create_topup_entry` only; load success
`promo_amount>0` bot rows only).

## REMAINING_EXCEPTIONS

```text
FINDING-006: FALSE_POSITIVE / ROUTE_C; not closed (CLOSURE_OPERATOR not this hop);
  FINDING_TERMINAL=no; not a HARD_BLOCK candidate by itself
Residual intake: empty (item 6 was last); FINDING-007 not created
ROOT-001: different closed family; do not reopen; FAMILY-FANIN.md not overwritten
FINDING-002 / HC-001: different closed family; do not reopen
FINDING-003: closed_false_positive; do not reopen
FINDING-004 / HC-FINDING-004-STALE-TEST: different closed family; do not reopen
FINDING-005: closed_fixed; do not reopen
```

No residual intake remains. No open SAME_INVARIANT candidate remains.
CASE stays OPEN until CLOSURE_OPERATOR. Not HARD_BLOCK_READY.

## BRANCH_SUMMARY

| FINDING_ID | ROLE | EPISODE_TERMINAL | RED | FIX | GREEN | OWNER_PRODUCTION_GO | NOTES |
|---|---|---|---|---|---|---|---|
| FINDING-006 | episode root (sequential residual, INTAKE-001 item 6) | pending (FALSE_POSITIVE classified; not closed) | N/A | N/A | N/A | N/A | FALSE_POSITIVE / ROUTE_C; FINDING_TERMINAL=no |
| ROOT-001 | other family | FIXED | results/RED-ROOT-001.md | results/FIX-ROOT-001.md | results/GREEN-ROOT-001.md | N/A | closed_fixed; out-of-episode; do not reopen |
| FINDING-002 | other family | FIXED | results/RED-FINDING-002.md | results/FIX-FINDING-002.md | results/GREEN-FINDING-002.md | N/A | closed_fixed; out-of-episode; do not reopen |
| HC-001 | other family SAME_INVARIANT of FINDING-002 | FIXED | results/RED-HC-001.md | results/FIX-HC-001.md | results/GREEN-HC-001.md | N/A | closed_fixed; not open_candidate; out-of-episode; do not reopen |
| FINDING-003 | other episode | FALSE_POSITIVE | N/A | N/A | N/A | N/A | closed_false_positive; do not reopen |
| FINDING-004 | other family | FIXED | results/RED-FINDING-004.md | results/FIX-FINDING-004.md | results/GREEN-FINDING-004.md | N/A | closed_fixed; out-of-episode; do not reopen |
| HC-FINDING-004-STALE-TEST | other family SAME_INVARIANT of FINDING-004 | FIXED | results/RED-HC-FINDING-004-STALE-TEST.md | tests/unit/wb/utils/test_promo_accounting.py | results/GREEN-HC-FINDING-004-STALE-TEST.md | N/A | closed_fixed / INTEGRATED; not open_candidate; out-of-episode; do not reopen |
| FINDING-005 | other family | FIXED | results/RED-FINDING-005.md | results/FIX-FINDING-005.md | results/GREEN-FINDING-005.md | N/A | closed_fixed; out-of-episode; do not reopen |

Started branches for THIS episode: FINDING-006 only (classified FALSE_POSITIVE,
not closed). No hunt child. No `open_candidate` SAME_INVARIANT residual.

LEDGER `## BRANCH_REGISTRY` (read-only snapshot; this worker does not mutate it):

```text
HUNT_PASSES_EXECUTED: 1
MAX_DEPTH_SEEN: 0
ACTIVE_BRANCH_COUNT: 1
MAX_HUNT_PASSES: 3
MAX_DEPTH_FROM_ROOT: 3
MAX_ACTIVE_BRANCHES: 3
MAX_ACTIVE_FINDINGS: 1
ROOT-001 DEPTH=0 EPISODE_TERMINAL=FIXED
FINDING-002 DEPTH=0 EPISODE_TERMINAL=FIXED
HC-001 PARENT=FINDING-002 DEPTH=1 EPISODE_TERMINAL=FIXED
FINDING-003 DEPTH=0 EPISODE_TERMINAL=FALSE_POSITIVE
FINDING-004 DEPTH=0 EPISODE_TERMINAL=FIXED
HC-FINDING-004-STALE-TEST PARENT=FINDING-004 DEPTH=1 EPISODE_TERMINAL=FIXED
FINDING-005 DEPTH=0 EPISODE_TERMINAL=FIXED
FINDING-006 DEPTH=0 EPISODE_TERMINAL empty (FALSE_POSITIVE classified; not closed)
```

FINDING-006 is a sequential residual from INTAKE-001 item 6, not a hunt child
of ROOT-001 / FINDING-002 / FINDING-003 / FINDING-004 / FINDING-005.
LEDGER `ACTIVE_BRANCH_COUNT=1` is the claimed FINDING-006 episode, not a hunt
child. Hunt children = 0.

## HUNT_SUMMARY

```text
HUNT_RESULT: CLEAR
HUNT_PASSES_EXECUTED: 1
MAX_HUNT_PASSES: 3
CANDIDATE_COUNT: 0
CANDIDATES: []
OPEN_SAME_INVARIANT_CANDIDATES: NONE
HUNT_PACKET: team/packets/WEX_BOUNDED_HUNTER_14c710e724.out.json
HUNT_WORKER: WEX/BOUNDED_HUNTER/14c710e724
HUNT_PROOF: results/PROOF-HUNT-BOUNDED-HUNTER-FINDING-006.md
PRODUCTION_SIBLING_REMAINING: none
```

## SAME_INVARIANT_SCAN

Scan of hunt packet / proof, `findings/HC-*`, `findings/FINDING-*`, input
payload, and LEDGER residuals for `STATUS ∈ {open_candidate, OPEN_CANDIDATE}`
and `RELATION_TO_ROOT_CANDIDATE=SAME_INVARIANT_FINDING`:

```text
WEX_BOUNDED_HUNTER_14c710e724
  HUNT_RESULT: CLEAR
  CANDIDATES: []
findings/FINDING-006.md
  STATUS: claimed
  OPEN_CANDIDATE: NO
findings/HC-001.md
  STATUS: closed_fixed
  RELATION_TO_ROOT_CANDIDATE: SAME_INVARIANT_FINDING (FINDING-002 family)
  OPEN_CANDIDATE: NO
  OUT_OF_EPISODE: YES
findings/HC-FINDING-004-STALE-TEST.md
  STATUS: closed_fixed
  RELATION_TO_ROOT_CANDIDATE: SAME_INVARIANT_FINDING (FINDING-004 family)
  OPEN_CANDIDATE: NO
  OUT_OF_EPISODE: YES
findings/ROOT-001.md STATUS: closed_fixed OPEN_CANDIDATE: NO
findings/FINDING-002.md STATUS: closed_fixed OPEN_CANDIDATE: NO
findings/FINDING-003.md STATUS: closed_false_positive OPEN_CANDIDATE: NO
findings/FINDING-004.md STATUS: closed_fixed OPEN_CANDIDATE: NO
findings/FINDING-005.md STATUS: closed_fixed OPEN_CANDIDATE: NO
HARD_BLOCK_READY: false
BLOCKING_FINDINGS: []
OPEN_SAME_INVARIANT_CANDIDATES: NONE
BLOCKS_ROOT_CLOSURE: false
```

No true remaining `open_candidate` SAME_INVARIANT. HARD_BLOCK does not fire.
Do not list a closed HC as OPEN_CANDIDATE / non-blocking residual.

## CLOSURE_READINESS

```text
CLOSURE_READINESS: READY_FOR_CLOSURE
SCOPE: FINDING-006 episode only
FINDING_TERMINAL: no
MISSION_COMPLETE: no
BLOCKS_ROOT_CLOSURE: false
BLOCKING_FINDINGS: []
OPEN_SAME_INVARIANT_CANDIDATES: NONE
NO_OPEN_SAME_INVARIANT_CANDIDATES: true
HARD_BLOCK_READY: false
FANIN_STATUS: FANIN_READY
LEARNING_READY: NOT_CLAIMED
LEARNING_STARTED: no
CLOSURE_STARTED: no
CASE_STATUS: OPEN
LEAVE_OPEN_REASON:
RESIDUAL_INTAKE_ITEMS: []
CLASS_STATUS: OPEN
CLASS_LEVEL_GO_WRITE: FORBIDDEN
```

FINDING-006 is classified FALSE_POSITIVE / ROUTE_C and not closed. Episode
FANIN is READY because hunt is CLEAR and no SAME_INVARIANT `open_candidate`
remains. Residual intake is empty. Case remains OPEN until CLOSURE_OPERATOR.
`LEARNING_READY` is not claimed as FANIN_READY. `MISSION_COMPLETE=no`
(closure owns case complete).

## REGRESSION_STATUS

```text
FINDING-006: FALSE_POSITIVE / ROUTE_C / CLOSED_NO_IMPLEMENTATION
  RED: N/A
  FIX: N/A
  GREEN: N/A
EPISODE: FANIN_READY
COMMIT_CREATED: NO
```

## LIMITS_CHECK

```text
LIMITS_CHECK: PASS
HUNT_PASSES_EXECUTED: 1 <= MAX_HUNT_PASSES: 3
MAX_DEPTH_SEEN: 0 <= MAX_DEPTH_FROM_ROOT: 3
ACTIVE_BRANCH_COUNT: 1 <= MAX_ACTIVE_BRANCHES: 3
DEPTH: 0
MAX_ACTIVE_FINDINGS: 1
```

Limits are not exceeded. Hunt children = 0. LEDGER active count is the
claimed FINDING-006 episode.

## CHECKS

```text
1_FIXED_HAVE_RED_GREEN_GO: N/A
   FALSE_POSITIVE / ROUTE_C. No RED, no GREEN, no Owner production GO.
   CLOSED_NO_IMPLEMENTATION.
2_NO_WEAKEN: N/A
   No test or production change in this episode.
3_NO_DOUBLE_FIX: PASS
   No production fix. Did not reopen or re-patch ROOT-001 / FINDING-002 /
   HC-001 / FINDING-003 / FINDING-004 / HC-FINDING-004-STALE-TEST /
   FINDING-005 paths.
4_NO_CONFLICTING_PRODUCTION_DIFFS: N/A
   No production diff from this episode. Closed families and
   FAMILY-FANIN.md not touched by this assembler.
5_ONE_ROOT_INVARIANT_OR_EXPLICIT_OUTEPISODE: PASS
   Episode invariant is JOURNAL-BOT-ONLY. Hunt CLEAR: no SAME_INVARIANT
   sibling. Closed families are explicit out-of-episode. No open
   SAME_INVARIANT candidate remains.
6_LIMITS_NOT_EXCEEDED: PASS
   Hunt passes / depth / active branches within limits.
```

Checks 1-2 N/A (Route C; Owner-noted no-implementation exception).
Checks 3-6 PASS. HARD_BLOCK_READY=false. Assembly complete.
STATUS=FANIN_READY.

## NEXT_ACTION

```text
/opsx-learn-from-bug case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z FANIN_PATH=.opsx/runs/bug-cases/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/results/FANIN.md
```

Do not paste `mode=resume-family-fanout` — no open SAME_INVARIANT candidate
remains. `LEARNING_READY=NOT_CLAIMED` (learning is the next worker; this
assembler does not claim it).

Do not create FINDING-007. Do not reopen ROOT-001 / FINDING-002 / HC-001 /
FINDING-003 / FINDING-004 / HC-FINDING-004-STALE-TEST / FINDING-005.
Do not write FAMILY-FANIN.md from this assembler. Do not write LEDGER /
CASE / INDEX / findings / ROUTE-TRACE / CHECKPOINT / production / tests.
Do not close FINDING-006. Do not claim MISSION_COMPLETE=yes.

COMMIT_ALLOWED: NO
MISSION_COMPLETE: no
FINDING_TERMINAL: no
LEARNING_READY: NOT_CLAIMED
