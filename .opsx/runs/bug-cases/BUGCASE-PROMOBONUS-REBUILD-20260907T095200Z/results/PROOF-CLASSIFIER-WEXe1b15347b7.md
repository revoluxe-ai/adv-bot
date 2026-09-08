# PROOF-CLASSIFIER-WEXe1b15347b7

WORKER_ID: CLASSIFIER
WORKER_EXECUTION_ID: WEX/CLASSIFIER/e1b15347b7
ORCHESTRATION_ID: ORCH/sup-promo-t07-d07
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-003
COMPLETED_AT: 2026-09-07T15:42:02Z
MAPS_TO: /opsx-classify-bug
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-003/2026-09-07T15:33:26Z

## Classification

CLASSIFICATION: FALSE_POSITIVE
CHOSEN_ROUTE: ROUTE_C
EXPECTED_NEXT_COMMAND: CLOSED_NO_IMPLEMENTATION
EXPECTED_EXECUTION_ROUTE: CLOSED_NO_IMPLEMENTATION
ACTUAL_NEXT_COMMAND: NOT_APPLICABLE
ACTUAL_EXECUTION_ROUTE: NOT_APPLICABLE
NEXT_COMMAND_RECONCILIATION: NOT_APPLICABLE
ROUTE_RECONCILIATION: NOT_APPLICABLE
CURRENT_ROUTE_STATE: CLOSED_NO_IMPLEMENTATION
OPENSPEC_UPDATE_REQUIRED: no

## Actions

- Read input packet PKT/WEX/CLASSIFIER/e1b15347b7/IN
- Read findings/FINDING-003.md, intakes/INTAKE-001.md, LEDGER.md (read-only except LEDGER ## ROUTE_STATE)
- Classified only FINDING-003 (INTAKE-001 HIGH item 3). Residual items 4-6 not started. ROOT-001 / FINDING-002 / HC-001 not reopened.
- Compared promo_ledger leftover-usable load to PromoStateService UPD ingest lookback and Owner OR/AND availability
- Did not claim; did not materialize FINDING-004..006; did not write RED/tests; did not fix; did not commit
- Appended one results/ROUTE-TRACE.jsonl event via runtime/route_trace.py (EVENT_TYPE=classification_route_selection; not WORKER_COMPLETED)
- Did not edit findings/FINDING-003.md, CASE.md, intakes/**, INDEX.md, handoffs/**, app/**, tests/**, team/CHECKPOINT.json, team/intents/**, OpenSpec

## Evidence

- Reported site: `promo_ledger.py` 90-day lookback allegedly drops campaign remaining into a false AND-stop versus Owner availability law
- `PROMO_LOOKBACK_DAYS = 90` is documented as the UPD ingest recovery window (`PromoStateService._UPD_LOOKBACK_DAYS` / `_resolve_upd_from_date`), not a leftover load filter
- Leftover-usable path `load_campaign_ledgers` calls `load_success_tranches` / `load_spend_rows` with no `cutoff`. Module comments: living leftover older than 90d must remain usable; inbound and spend windows stay aligned
- Production caller: `PromoStateService.refresh` -> `load_campaign_ledgers(...)` without cutoff. No other `app/` caller of the loaders
- Optional `cutoff=` on the loaders is unused on leftover-usable. Applying it would be a future footgun, not the current remaining-drop path
- Owner availability: `resolve_promo_availability` is OR pool/campaign; `PromoAvailability.stop_on_exhaustion` is true only when both sources are unusable (AND-stop)
- A 90-day UPD ingest miss omits spend rows (would inflate remaining if allocations are loaded), the opposite of dropping leftover remaining into a false AND-stop
- OpenSpec `openspec/decisions/index.md` has no promo leftover-lookback decision. Not SPEC_GAP: the alleged drop is not present on the leftover-usable production path
- Not item 4 (FEFO expired tranches), item 5 (leftover fraction), or item 6 (manual deposits)

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/Python/packet writes
- Artifacts written via Cursor Write tool (utf-8 path writes)
- Windows Shell JSON/JSONL write safety: Write->path; encoding=utf-8; route-trace append via `.cursor/pipeline/bug-team/runtime/route_trace.py` after Write of a staging JSON file (ensure_ascii=True on the staging object)

## Outcome

STATUS: PASS
CLASSIFICATION: FALSE_POSITIVE
NEXT_ACTION: CLOSED_NO_IMPLEMENTATION
MISSION_COMPLETE: no
FINDING_TERMINAL: no
