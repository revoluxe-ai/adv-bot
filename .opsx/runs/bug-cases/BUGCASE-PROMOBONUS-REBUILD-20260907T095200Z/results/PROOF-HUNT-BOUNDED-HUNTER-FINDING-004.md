# Bounded hunt proof — FEFO-SPEND-SKIP-EXPIRED

```text
WORKER_ID: BOUNDED_HUNTER
WORKER_EXECUTION_ID: WEX/BOUNDED_HUNTER/4e8665d743
ORCHESTRATION_ID: ORCH/sup-promo-t08-d08
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-004
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/FEFO-SPEND-SKIP-EXPIRED
HUNT_RESULT: CANDIDATES_FOUND
CANDIDATE_COUNT: 1
MAPS_TO: /opsx-bug-hunt bounds
COMPLETED_AT: 2026-09-07T17:36:28Z
```

TOPIC_INTENT: PRODUCT_BRIEF
SOURCE_RESOLUTION: DIRECT (input packet, findings/FINDING-004.md, GREEN/FIX/RED FINDING-004, scoped promo_accounting apply_spend_fefo + callers + nearest tests)
EXECUTION_PREFLIGHT: git status SKIP_IF (not required for hunt decision); Pass 1 rg bounded to apply_spend_fefo / is_expired spend loop. JSON/packet writes via Write tool to path (anti-heredoc; no bash cat <<EOF). Windows Shell JSON/JSONL write safety: Write->path, encoding=utf-8, ensure_ascii=True.

Verdict:
- plan_only (hunt only; no fix, no RED, no classify, no close)

Base/head:
- base: not required (packet-scoped hunt; git identity SKIP_IF)
- head: not required
- current branch: deferred_not_required
- inspected snapshot: current worktree after FINDING-004 production skip-expired fix
- dirty files: not inspected (not REQUIRED_FOR hunt decision)

Invariant:
- apply_spend_fefo must not apply spend to expired leftover before live leftover; expired 300 + live 200 + spend 50 must yield remaining 150.

Root finding packet:
- root finding id: FINDING-004
- title: promo_accounting.py FEFO applies spend to expired leftover first, inflating live remaining
- confirmed verdict: IMPLEMENTATION_BUG / ROUTE_A (upstream packet; not reclassified here)
- causal boundary: FEFO spend loop consumed expired leftover first; remaining counted only live leftover
- write boundary: derived campaign remaining / overlay fraction
- pre-fix remaining: 200; post-fix remaining: 150 (GREEN_CONFIRMED on frozen node)

## Hunt bound

Find only same-invariant sites that apply spend to expired leftover before live leftover (inflating live remaining). Production fix already skips is_expired in apply_spend_fefo. Do not hunt intake items 5-6 leftover-fraction or journal unless they literally apply spend to expired leftover. Do not hunt ROOT-001 overlay, FINDING-002 pool-failure, or FINDING-003 90d leftover cutoff. Do not reopen closed findings. Do not fix, write RED, classify, or close. Sibling test test_fefo_spend_and_expired_tranche_unusable asserting remaining==200 may be recorded as a candidate if it encodes the same inflation; do not treat it as a new root. If no remaining production sibling, HUNT_RESULT may be CLEAR or CANDIDATES_FOUND for the stale test only.

FINDING-004 production skip is already in place. Not reclassified. Not fixed this hop. No RED. Not closed. No Route A/B/C/D chosen. Intake items 5-6 not started. FINDING-005 not allocated.

## Result

HUNT_RESULT: CANDIDATES_FOUND. No remaining production sibling. One stale-test candidate encodes the same inflation (remaining==200 after expired 300 + live 200 + spend 50).

CANDIDATE: HC-FINDING-004-STALE-TEST. Not a new root. RELATION_CLASSIFIER owns relation. Optional hint: same-invariant stale assertion, not a production spend loop.

## KNOWN_ROOT_RESULT

```text
ROOT_FINDING_ID: FINDING-004
STATUS: not_reproduced_on_inspected_snapshot
SNAPSHOT: current worktree apply_spend_fefo (post-fix)
LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:188
MATCHED_EFFECT: spend loop continues when is_expired(item.expires_at, now=now); expired leftover no longer absorbs spend
MATCHED_CAUSAL_PATH: leftovers FEFO-sorted -> skip expired -> take from live leftover -> remaining sums live leftover only
MATCHED_WRITE_BOUNDARY: campaign remaining / fraction via campaign_ledger_from_rows
EVIDENCE: lines 187-194 skip expired; remaining filter 199-203 also skips expired; GREEN remaining==150
ACTION: do not emit FINDING-004 as a hunt candidate; do not reopen closed findings
```

## NEW_FINDINGS

### 1. HC-FINDING-004-STALE-TEST [stale_test_same_inflation] remaining==200 sibling

```text
HUNT_CANDIDATE_ID: HC-FINDING-004-STALE-TEST
File: tests/unit/wb/utils/test_promo_accounting.py
LOC_LINK: tests/unit/wb/utils/test_promo_accounting.py:67
Function: test_fefo_spend_and_expired_tranche_unusable
Boundary: frozen unit assertion on apply_spend_fefo remaining
RELATION_TO_ROOT_CANDIDATE: SAME_INVARIANT_FINDING (hint only; not classifier authority)
CONFIDENCE: high
ADJUDICATION_REQUIRED: true
CHILD_CHAT_RECOMMENDED: false
NOT_A_NEW_ROOT: true
NOT_FINDING_005: true
```

Evidence:

- Same fixture as the frozen GREEN node: expired leftover 300 (expires_at=_dt(-1)) + live leftover 200 (expires_at=_dt(5)) + spend 50 at NOW.
- Line 67 asserts `remaining == 200` (pre-fix inflation: expired leftover absorbed spend; live remaining stayed 200).
- Frozen FINDING-004 node `test_fefo_spend_hits_live_leftover_not_expired` asserts `remaining == 150` on the same inputs (lines 71-105).
- GREEN-FINDING-004 adjacent file run: sibling FAILED `assert 150 == 200` at line 67 after the production skip-expired fix.
- RED-FINDING-004 already recorded this sibling as bug-encoding and did not reuse it as the passing expectation.
- Frozen TEST_CONTENT_SHA256 `cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2` was not edited (hunter did not write RED / did not edit tests).
- This is not a second production spend loop. Production callers already use the fixed apply_spend_fefo.

## Pass 1 scan (cheap)

`apply_spend_fefo` definition + direct callers:

| Site | Applies spend to expired leftover before live leftover? | Classification |
|------|--------------------------------------------------------|----------------|
| `promo_accounting.py` apply_spend_fefo spend loop | No (FINDING-004 fix: `continue` on `is_expired`) | duplicate_root / fixed; not a candidate |
| `promo_accounting.py` remaining sum | No (skips expired leftover when summing usable remaining) | same function remaining filter; not a sibling spend loop |
| `campaign_ledger_from_rows` | No (calls fixed apply_spend_fefo only) | wrapper; not a candidate |
| `promo_ledger.load_campaign_ledgers` | No (calls campaign_ledger_from_rows; no local spend-to-expired loop) | caller of fixed helper; not a candidate |
| `test_fefo_spend_hits_live_leftover_not_expired` | N/A (frozen GREEN node; remaining==150) | root RED/GREEN; not a candidate |
| `test_fefo_spend_and_expired_tranche_unusable` | Assertion encodes remaining==200 on the same fixture | HC-FINDING-004-STALE-TEST |
| `test_campaign_ledger_fraction_uses_remaining_not_ceiling` remaining==200 | No spend + no expired leftover (live 200, spend empty) | different fixture; not same inflation |
| `test_or_active_and_stop` remaining=200 constructor | Constructed ledger, no apply_spend_fefo | out of invariant |

`apply_spend_fefo` production writers: only `app/shared/domains/wb/utils/promo_accounting.py`. Sole production caller: `campaign_ledger_from_rows` in the same module. Downstream ledger load (`promo_ledger.load_campaign_ledgers`) delegates to that caller.

## Excluded (bound, not hunted as siblings)

- Intake items 5-6 leftover-fraction / journal: no independent spend-to-expired leftover loop found at `apply_spend_fefo` callers. Not started. FINDING-005 / FINDING-006 not allocated.
- ROOT-001 overlay (closed_fixed): not reopened.
- FINDING-002 pool-failure (closed_fixed): not reopened.
- HC-001 (closed_fixed / INTEGRATED): not reopened.
- FINDING-003 90d leftover cutoff (closed_false_positive): not reopened.
- Leftover-fraction journal / promo_state_service pool path / overlay view provider / promo_ledger lookback: out of this invariant unless they literally apply spend to expired leftover (they do not).

## Hunter boundary (held)

```text
HUNTER_IMPLEMENTED_FIX: false
HUNTER_WROTE_RED: false
HUNTER_CHOSE_ROUTE: false
HUNTER_CLOSED_CANDIDATE: false
COMMIT_ALLOWED: NO
```

HUNT_EFFECTIVENESS: HIGH_WITHIN_DECLARED_SCOPE: enumerated apply_spend_fefo definition, remaining filter, sole production caller campaign_ledger_from_rows, downstream load_campaign_ledgers, and nearest tests in test_promo_accounting.py. Production skip-expired reconfirmed. One stale sibling assertion remains.

HUNT_FALSE_NEGATIVE_RISK: BOUNDED_TO_APPLY_SPEND_FEFO: hunt matches sites that apply spend to expired leftover before live leftover. Items 5-6 leftover-fraction/journal not expanded. Overlay / pool-failure / 90d cutoff families not scanned. A second hidden spend-to-expired loop outside apply_spend_fefo callers would be outside this bound.

MISSION_COMPLETE: no
FINDING_TERMINAL: no
COMMIT_CREATED: NO
