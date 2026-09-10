# Bounded hunt proof — leftover-usable 90d cutoff

```text
WORKER_ID: BOUNDED_HUNTER
WORKER_EXECUTION_ID: WEX/BOUNDED_HUNTER/b69d090049
ORCHESTRATION_ID: ORCH/sup-promo-t07-d07
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-003
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-003/LEFTOVER-NO-90D-CUTOFF
HUNT_RESULT: CLEAR
CANDIDATE_COUNT: 0
MAPS_TO: /opsx-bug-hunt bounds
COMPLETED_AT: 2026-09-07T15:50:30Z
```

TOPIC_INTENT: PRODUCT_BRIEF
SOURCE_RESOLUTION: DIRECT (input packet, findings/FINDING-003.md read-only, classifier OUT, scoped promo_ledger + promo_state_service leftover loaders)
EXECUTION_PREFLIGHT: git status SKIP_IF (not required for hunt decision); Pass 1 rg bounded to leftover loaders / cutoff= / PROMO_LOOKBACK_DAYS

Verdict:
- plan_only

Base/head:
- base: not required (packet-scoped hunt; git identity SKIP_IF)
- head: not required
- current branch: deferred_not_required
- inspected snapshot: current worktree leftover-usable loaders
- dirty files: not inspected (not REQUIRED_FOR hunt decision)

Invariant:
- Leftover-usable campaign remaining must not be filtered by the 90-day UPD ingest lookback; living leftover older than 90d stays usable.

Root finding packet:
- root finding id: FINDING-003
- title: promo_ledger.py 90-day lookback drops campaign remaining
- confirmed verdict: FALSE_POSITIVE / ROUTE_C (CLASSIFIER; not reclassified here)
- classification: FALSE_POSITIVE
- causal boundary: leftover-usable load alleged to apply 90d ingest window as remaining cutoff
- write boundary: derived campaign remaining / overlay availability
- pre-fix ref: classifier OUT PKT/WEX/CLASSIFIER/e1b15347b7/OUT; findings/FINDING-003.md

Scan scope:
- inspected: promo_ledger.py load_campaign_ledgers / load_success_tranches / load_spend_rows; promo_state_service.py load_campaign_ledgers call and _resolve_upd_from_date; app/ callers of those loaders; app/ cutoff= ; PROMO_LOOKBACK_DAYS / timedelta(days=_UPD_LOOKBACK_DAYS)
- expanded: none beyond leftover-cutoff caller hunt
- skipped: FEFO / leftover fraction / journal (intake 4-6); FINDING-002 pool-failure; reopen of ROOT-001 / FINDING-002 / HC-001; app/** edits; tests/**; OpenSpec

## Hunt bound

FINDING-003 is FALSE_POSITIVE: leftover-usable load does not apply the 90d ingest window as leftover cutoff. Hunt ONLY sibling sites that actually pass PROMO_LOOKBACK_DAYS/90d cutoff into leftover-usable campaign remaining (the claimed drop path). Do not hunt FEFO, leftover fraction, or journal (intake items 4-6) as same-invariant unless they literally apply leftover cutoff. Do not hunt FINDING-002 pool-failure. Do not reopen closed findings ROOT-001 / FINDING-002 / HC-001. If no leftover-cutoff caller exists, HUNT_RESULT=CLEAR.

FINDING-003 stays FALSE_POSITIVE / ROUTE_C. Not reclassified. Not fixed. No RED. Not closed. No Route A/B/C/D chosen. Intake items 4-6 not started as FINDING-004..006.

## Result

HUNT_RESULT: CLEAR. No production leftover-usable caller passes `PROMO_LOOKBACK_DAYS` / 90d `cutoff=` into `load_success_tranches` / `load_spend_rows` / leftover campaign remaining. `CANDIDATES=[]`. No new finding files.

## KNOWN_ROOT_RESULT

```text
ROOT_FINDING_ID: FINDING-003
STATUS: not_reproduced_on_inspected_snapshot
SNAPSHOT: current worktree leftover-usable load (post-classifier FALSE_POSITIVE)
LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:159
MATCHED_EFFECT: claimed remaining drop via 90d leftover cutoff is absent
MATCHED_CAUSAL_PATH: load_campaign_ledgers -> load_success_tranches/load_spend_rows with no cutoff
MATCHED_WRITE_BOUNDARY: leftover remaining is not filtered by PROMO_LOOKBACK_DAYS
EVIDENCE: leftover-usable production path does not pass cutoff; PROMO_LOOKBACK_DAYS is UPD ingest recovery only
ACTION: do not emit FINDING-003 as a hunt candidate; do not reclassify; do not reopen closed findings
```

DUPLICATE_ROOT_OBSERVATIONS:
- DUP-001: `load_campaign_ledgers` calls both loaders without cutoff (LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:159). Same causal path as the classified FALSE_POSITIVE, not a child.
- DUP-002: `PromoStateService.refresh` calls `load_campaign_ledgers` without cutoff (LOC_LINK: app/modules/auto_budget_manager/promo_state_service.py:189). Same leftover-usable writer, not a cutoff caller.

NEW_FINDINGS:
- none

Confirmed new production bugs:
- none

Findings requiring adjudication:
- none

Different-invariant candidates:
- none (UPD ingest 90d, FEFO expiry, leftover fraction, journal not started)

Adjacent / dead legacy / tests-only / false positives:
- optional `cutoff=` on loaders exists but unused on leftover-usable (LEGACY/footgun, not a caller)
- `_LookbackHonoringSession` in tests/unit/auto_budget_manager/test_promo_ledger.py is tests-only and the production leftover test calls `load_campaign_ledgers` without cutoff
- FINDING-003 itself remains CLASSIFIED FALSE_POSITIVE (not re-emitted)

## Pass 1 — leftover-cutoff callers

| Site | Passes 90d cutoff into leftover remaining? | Classification |
|------|--------------------------------------------|----------------|
| `load_campaign_ledgers` -> `load_success_tranches(session, ids)` | No. No `cutoff=` (LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:159) | FINDING-003 FALSE_POSITIVE path; not a candidate |
| `load_campaign_ledgers` -> `load_spend_rows(session, ids)` | No. No `cutoff=` (LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:160) | same |
| `PromoStateService.refresh` -> `load_campaign_ledgers(...)` | No. No cutoff kwarg (LOC_LINK: app/modules/auto_budget_manager/promo_state_service.py:189) | sole `app/` leftover-usable caller; not a cutoff caller |
| `load_success_tranches` / `load_spend_rows` optional `cutoff=` | Helper only. `if cutoff is not None` (LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:80 and :124). Zero `app/` call sites pass `cutoff=` | unused optional; not a leftover-cutoff caller |
| `_resolve_upd_from_date` / `get_costs_history(from_date=...)` | 90d is UPD ingest recovery, not leftover remaining load (LOC_LINK: app/modules/auto_budget_manager/promo_state_service.py:48) | different path; ingest miss would omit spend (inflate remaining), not drop leftover |
| Other `app/` `load_success_tranches(` / `load_spend_rows(` / `load_campaign_ledgers(` | None besides definitions + the two sites above | no sibling caller |

Repo-wide `cutoff=` in `app/`: none. Repo-wide leftover leftover-usable loader call sites: only `load_campaign_ledgers` (internal) and `PromoStateService.refresh` (production). Tests: `test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero` calls `load_campaign_ledgers` without cutoff.

`PROMO_LOOKBACK_DAYS` production uses: constant + leftover-usable no-cutoff comments in `promo_ledger.py`; `_UPD_LOOKBACK_DAYS` alias and `_resolve_upd_from_date` fallback in `promo_state_service.py`. No leftover remaining filter.

## Classified out of hunt bound (not candidates)

- FEFO / `is_expired` / `apply_spend_fefo` / `campaign_ledger_from_rows`: drops leftover via `expires_at <= now`, not `created_at` 90d lookback (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:65). Intake item 4. Not leftover cutoff.
- Leftover fraction / budget_after denominator: intake item 5. Does not pass 90d into remaining load.
- Journal / manual deposits: intake item 6. Does not pass leftover cutoff.
- FINDING-002 / HC-001 pool-failure Redis false-empty: different invariant; closed; not hunted.
- ROOT-001 Telegram rec-bid overlay: closed; not hunted.
- Token-monitoring / CSV exporter `cutoff_date`: unrelated domains.

## Why CLEAR

No leftover-cutoff caller exists. The claimed drop path (90d ingest window applied as leftover remaining cutoff) is not present on the leftover-usable production path. FINDING-003 remains FALSE_POSITIVE / ROUTE_C. No `findings/` candidate files written.

## HUNT_EFFECTIVENESS

HIGH_WITHIN_DECLARED_SCOPE: enumerated leftover-usable loaders and all production callers; confirmed zero `cutoff=` into leftover remaining; FINDING-003 not re-emitted; intake 4-6 and closed findings not opened.

## HUNT_FALSE_NEGATIVE_RISK

BOUNDED_TO_LEFTOVER_CUTOFF: hunt matches callers that pass `PROMO_LOOKBACK_DAYS` / 90d `cutoff=` into leftover-usable campaign remaining. Optional unused `cutoff=` helpers, UPD ingest recovery, FEFO expiry, leftover fraction, journal, FINDING-002 pool-failure, and closed ROOT-001 / HC-001 were classified out. `deep` flag absent; Pass 3 not expanded.

## FANOUT_INPUT

```text
ROOT_FINDING_ID: FINDING-003
INVARIANT: Leftover-usable campaign remaining must not be filtered by the 90-day UPD ingest lookback; living leftover older than 90d stays usable.
NEW_FINDING_IDS: (none)
CHILD_CHAT_CANDIDATES: (none)
ITEMS_NOT_REQUIRING_CHAT: FINDING-003 (FALSE_POSITIVE), ROOT-001, FINDING-002, HC-001, intake 4-6
PREREQ: do not emit GO; do not emit bare /opsx-fix-bug; do not materialize FINDING-004..006 from this hunt
```

LEARNING_INPUT_STATUS:
- ready
- blockers: none
- evidence available: this proof; leftover loaders; classifier FALSE_POSITIVE packet

Risks:
- optional unused `cutoff=` on loaders remains a future footgun if a later caller starts passing 90d into leftover remaining; that is not a current caller

Need from user:
- none

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/Python/packet writes
- Artifacts written via Cursor Write tool (utf-8 path writes)
- FINDING-003.md / ROOT-001.md / FINDING-002.md / HC-001.md / CASE.md / LEDGER.md / INDEX.md / ROUTE-TRACE.jsonl / app/** / tests/** not edited
