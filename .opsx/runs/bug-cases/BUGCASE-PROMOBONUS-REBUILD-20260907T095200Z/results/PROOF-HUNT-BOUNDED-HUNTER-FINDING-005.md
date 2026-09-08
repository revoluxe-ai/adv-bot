# Bounded hunt proof — leftover fraction remaining / tranche.amount

```text
WORKER_ID: BOUNDED_HUNTER
WORKER_EXECUTION_ID: WEX/BOUNDED_HUNTER/03c32b90bf
ORCHESTRATION_ID: ORCH/sup-promo-t10-d10
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-005
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-005/LEFTOVER-FRACTION-TRANCHE-AMOUNT
HUNT_RESULT: CLEAR
CANDIDATE_COUNT: 0
MAPS_TO: /opsx-bug-hunt bounds
COMPLETED_AT: 2026-09-07T19:56:40Z
MISSION_COMPLETE: no
```

TOPIC_INTENT: PRODUCT_BRIEF
SOURCE_RESOLUTION:
- mode: exact_path
- primary_path: findings/FINDING-005.md
- fallback_used: false
- search_operations: 3 scoped rg (leftover mix keywords in wb/utils; campaign_ledger_from_rows callers; promo_fraction_from_amounts / leftover tests)
- search_scope: packet HUNT_SCOPE + allowed promo_ledger / promo_plan_multiplier / test_promo_accounting
- unresolved_gap: none
EXECUTION_PREFLIGHT:
- git_branch: deferred_not_required
- git_status: skipped
- other_ops: Pass 1 rg bounded to leftover mix denominator (remaining / budget_after|campaign_budget_total)
- blocked_on_preflight: false
JSON/packet writes via Write tool to path (anti-heredoc; no bash cat <<EOF). Windows Shell JSON write safety: Write->path, encoding=utf-8, ensure_ascii=True.

Verdict:
- plan_only (hunt only; no fix, no RED, no classify, no close)

Base/head:
- base: not required (packet-scoped hunt; git identity SKIP_IF)
- head: not required
- current branch: deferred_not_required
- inspected snapshot: current worktree after FINDING-005 leftover-fraction fix (GREEN_CONFIRMED)
- dirty files: not inspected (not REQUIRED_FOR hunt decision)

Invariant:
- campaign leftover fraction must use remaining over the top-up unit (tranche.amount), not budget_after or campaign_budget_total. leftover remaining 200 with amount 1000 and budget_after 12000 must yield fraction 0.2 (M=1.25), not 200/12000.

Root finding packet:
- root finding id: FINDING-005
- title: campaign leftover fraction uses budget_after/total so M collapses
- confirmed verdict: IMPLEMENTATION_BUG / ROUTE_A (upstream packet; not reclassified here)
- classification: IMPLEMENTATION_BUG
- causal boundary: leftover mix used campaign_budget_total when present, else apply_spend_fefo reference_budget overwritten to leftover budget_after
- write boundary: CampaignPromoLedger.fraction (derived overlay M)
- pre-fix ref: PRODUCTION_HASH_BEFORE sha256:4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b (results/RED-FINDING-005.md)

## Hunt bound

Find only same-invariant sites that compute leftover mix fraction as remaining / (budget_after or campaign_budget_total) so M collapses. Production mix now uses remaining / tranche.amount. Do not hunt intake item 6 journal/manual deposits unless it literally uses leftover budget_after as mix denominator. Do not hunt ROOT-001 overlay, FINDING-002 pool-failure, FINDING-003 90d cutoff, or FINDING-004 FEFO expired-spend. Do not reopen closed findings. Do not fix, write RED, classify, or close. A stale test that encodes leftover remaining/budget_after collapse may be a candidate; do not treat it as a new root. If no remaining production sibling, HUNT_RESULT may be CLEAR or CANDIDATES_FOUND for a stale test only.

FINDING-005 production leftover mix is already remaining / tranche.amount. Not reclassified. Not fixed this hop. No RED. Not closed. No Route A/B/C/D chosen. Intake item 6 not started. Closed ROOT-001 / FINDING-002 / HC-001 / FINDING-003 / FINDING-004 / HC-FINDING-004-STALE-TEST not reopened.

## Result

HUNT_RESULT: CLEAR. No remaining production sibling computes leftover mix as remaining / (budget_after|campaign_budget_total). No stale test encodes leftover remaining/budget_after collapse (the frozen node asserts 0.2; the older equal-1000 sibling does not encode 200/12000). CANDIDATES=[]. No new finding files.

## KNOWN_ROOT_RESULT

```text
ROOT_FINDING_ID: FINDING-005
STATUS: not_reproduced_on_inspected_snapshot
SNAPSHOT: current worktree campaign_ledger_from_rows / apply_spend_fefo (post-fix)
LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:212
MATCHED_EFFECT: leftover mix denominator is last live leftover tranche.amount; budget_after and campaign_budget_total do not set f
MATCHED_CAUSAL_PATH: apply_spend_fefo reference_budget=row.amount -> campaign_ledger_from_rows promo_fraction_from_amounts(remaining, reference); campaign_budget_total discarded
MATCHED_WRITE_BOUNDARY: CampaignPromoLedger.fraction
EVIDENCE: reference_budget = row.amount (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:212); del campaign_budget_total (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:245); mix remaining/reference (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:251); GREEN remaining 200 / amount 1000 / budget_after 12000 => fraction 0.2 (M=1.25)
ACTION: do not emit FINDING-005 as a hunt candidate; do not reopen closed findings; do not start item 6
```

DUPLICATE_ROOT_OBSERVATIONS:
- DUP-001: apply_spend_fefo sets reference_budget from row.amount, not budget_after (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:212). Same causal path as FINDING-005, now correct. Not a child.
- DUP-002: campaign_ledger_from_rows discards campaign_budget_total and mixes remaining over that reference (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:245). Same write boundary as the known root. Not a child.
- DUP-003: load_campaign_ledgers still passes campaign_budget_total into campaign_ledger_from_rows (LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:175). Unused for mix after the fix. Same caller path, not a second leftover-denominator site.

NEW_FINDINGS:
- none

Confirmed new production bugs:
- none

Findings requiring adjudication:
- none

Different-invariant candidates:
- none started. pool_usable_from_pick uses cashback_sum / topup_amount (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:278) — FINDING-002 pool mix, not leftover remaining/(budget_after|campaign_budget_total). CREATE_SEPARATE_ROOT_CANDIDATE not opened (bound forbids hunting FINDING-002).

Adjacent / dead legacy / tests-only / false positives:
- ADJ-001: test_campaign_ledger_fraction_uses_remaining_not_ceiling uses amount=budget_after=campaign_budget_total=1000 and asserts fraction 0.2 (LOC_LINK: tests/unit/wb/utils/test_promo_accounting.py:149). Weak coverage; does not encode leftover remaining/budget_after collapse. Not a stale-test candidate.
- TEST-001: test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after is the FINDING-005 frozen node asserting 0.2 / M=1.25 (LOC_LINK: tests/unit/wb/utils/test_promo_accounting.py:171). Duplicate of the known root regression, not a child.
- promo_overlay.fraction_from_cached_state reads cached effective_fraction (LOC_LINK: app/shared/domains/wb/utils/promo_overlay.py:16). ROOT-001 overlay consumer; does not recompute leftover mix from budget_after. Skipped.
- auto_budget_manager.service budget_after persist is verification storage, not leftover mix. Skipped.
- Intake item 6 journal/manual deposits: not started; no leftover budget_after mix denominator found on that path.

## Pass 1 — leftover mix denominators

| Site | leftover mix = remaining / (budget_after|campaign_budget_total)? | Classification |
|------|------------------------------------------------------------------|----------------|
| apply_spend_fefo reference_budget | No. Last live leftover `row.amount` (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:212) | FINDING-005 post-fix; DUP-001 |
| campaign_ledger_from_rows | No. `del campaign_budget_total`; `promo_fraction_from_amounts(remaining, reference)` (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:245) | FINDING-005 post-fix; DUP-002 |
| load_campaign_ledgers | No. Passes `campaign_budget_total` but mix ignores it (LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:175) | same caller; DUP-003 |
| promo_fraction_from_amounts | Generic `promo_amount/total_amount` helper (LOC_LINK: app/shared/domains/wb/utils/promo_plan_multiplier.py:27) | no leftover/budget_after logic |
| pool_usable_from_pick | No leftover remaining. Uses `cashback_sum / topup_amount` (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:278) | different invariant; skipped |
| test leftover 200/1000/12000 | Asserts 0.2, not 200/12000 (LOC_LINK: tests/unit/wb/utils/test_promo_accounting.py:171) | known-root frozen test |
| test remaining_not_ceiling | Equal 1000s; asserts 0.2 (LOC_LINK: tests/unit/wb/utils/test_promo_accounting.py:149) | ADJ-001 weak; not collapse encoding |

Pass 2: inspected the 6 strongest sites above. No distinct leftover-denominator bypass. Pass 3 / `deep` absent; PASS_3=MANDATORY_STOP; no new working branches.

## Classified out of hunt bound (not candidates)

- ROOT-001 Telegram rec-bid overlay / promo_overlay cached fraction: closed; not leftover mix recompute.
- FINDING-002 / HC-001 pool-failure Redis false-empty / pool_usable_from_pick: different invariant; closed; not hunted.
- FINDING-003 leftover 90d cutoff: closed_false_positive; not leftover mix.
- FINDING-004 / HC-FINDING-004-STALE-TEST FEFO expired-spend: closed; not leftover mix.
- Intake item 6 journal / manual deposits: not started.

## Why CLEAR

The known root leftover collapse (remaining 200 / wallet 12000) is gone on the inspected post-fix snapshot. The only leftover mix writer is `campaign_ledger_from_rows` using `remaining / tranche.amount`. No sibling production path and no stale test still encodes remaining/(budget_after|campaign_budget_total). FINDING-005 is not re-emitted. No `findings/` candidate files written.

## HUNT_EFFECTIVENESS

HIGH_WITHIN_DECLARED_SCOPE: enumerated apply_spend_fefo reference_budget, campaign_ledger_from_rows mix, sole production caller load_campaign_ledgers, promo_fraction_from_amounts call sites, and leftover-fraction tests. Production remaining/tranche.amount reconfirmed. No stale collapse assertion.

## HUNT_FALSE_NEGATIVE_RISK

BOUNDED_TO_LEFTOVER_FRACTION: hunt matches sites that compute leftover mix as remaining / (budget_after|campaign_budget_total). Pool next-topup mix, overlay consumers, FEFO spend skip, 90d leftover cutoff, and journal/manual deposits classified out. `deep` flag absent; Pass 3 not expanded.

## FANOUT_INPUT

```text
ROOT_FINDING_ID: FINDING-005
INVARIANT: leftover fraction remaining / tranche.amount, not remaining / (budget_after|campaign_budget_total). Vector: remaining 200 / amount 1000 / budget_after 12000 => 0.2 not 200/12000.
NEW_FINDING_IDS: (none)
CHILD_CHAT_CANDIDATES: (none)
ITEMS_NOT_REQUIRING_CHAT: FINDING-005 (known root, not re-emitted), ROOT-001, FINDING-002, HC-001, FINDING-003, FINDING-004, HC-FINDING-004-STALE-TEST, intake item 6
PREREQ: do not emit GO; do not emit bare /opsx-fix-bug; do not materialize FINDING-006 from this hunt; do not close FINDING-005
```

LEARNING_INPUT_STATUS:
- ready
- blockers: none
- evidence available: this proof; FINDING-005 RED/FIX/GREEN; promo_accounting leftover mix; no HC candidate packets

Risks:
- load_campaign_ledgers still forwards campaign_budget_total; if a later edit reuses that kwarg as mix denominator, that would be a new same-invariant regression, not a current sibling.

Need from user:
- none

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/Python/packet writes
- Artifacts written via Cursor Write tool (utf-8 path writes)
- FINDING-005.md / ROOT-001.md / FINDING-002.md / HC-001.md / FINDING-003.md / FINDING-004.md / HC-FINDING-004-STALE-TEST.md / CASE.md / LEDGER.md / INDEX.md / ROUTE-TRACE.jsonl / app/** / tests/** not edited
- No findings/HC-* candidate (HUNT_RESULT=CLEAR)
- MISSION_COMPLETE: no
