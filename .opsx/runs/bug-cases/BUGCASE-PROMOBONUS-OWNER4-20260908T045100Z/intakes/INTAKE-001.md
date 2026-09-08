INTAKE_RECORD

CASE_ID: BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z
INTAKE_ID: INTAKE-001
CREATED_AT: 2026-09-08T04:51:00Z
SOURCE_TYPE: owner_report
SOURCE_REFERENCE: current user message / sequential bug mission prerequisite
RAW_REPORT:
1) MED promo_state_service.py / promo_ledger.py: success allocations are loaded without cutoff, but initial/recovery GET /adv/v1/upd ingest is limited to 90 days; spend outside the recovery window may be absent from PG and remaining can be overstated.
2) MED app/modules/shop_runner/service_manager/manager.py around line 826: watchdog refresh/derived overlay is observed on the next tick; 15-minute stale cache conservatively disables uplift while promo is live. Existing behavior is documented; materialize as a distinct finding for implementation/test decision.
3) MED adv_state.py: V3 Raise MAX composes with promo multiplier; flags are intentionally independent per Owner request, but effective value can exceed a 2x Owner ceiling. Materialize with semantic Owner decision unresolved; do not decide whether to cap.
4) LOW promo_accounting.py: cashback aliases are broader than documented Keshbek/Кэшбэк, and fingerprint without upd_num can collide across rows.
OBSERVED_SYMPTOM: Owner-listed promo-bonus signals requiring sequential adjudication.
KNOWN_CONTEXT: Intake-only prerequisite for a sequential bug mission. Item 2 is documented existing behavior and needs an implementation/test decision. Item 3 explicitly has an unresolved semantic Owner decision; this intake does not decide whether to cap. No code or test changes are authorized in this hop.
STATUS: intake_recorded
LAST_ACTIVITY_AT: 2026-09-08T05:03:00Z
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-MATERIALIZE-20260908"
DISPOSITION:
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID:
RESULT_PATH:
