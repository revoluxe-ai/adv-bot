INTAKE_RECORD

CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
INTAKE_ID: INTAKE-001
CREATED_AT: 2026-09-07T09:52:00Z
SOURCE_TYPE: independent_review
SOURCE_REFERENCE: invocation payload / MISSION_ID=SUP-PROMO-FIX-20260907 TASK_ID=T03-MATERIALIZE DISPATCH_ID=D03 WORKER_ID=W-MAT-01
RAW_REPORT:
Independent READ_ONLY review of uncommitted dirty promobonus rebuild. Six findings. No production migration. No commit/push/PR.

HIGH:
1. auto_shelf_bid_control_view_provider.py:881 — Telegram rec-bid uses get_effective_promo_plan(adv) without promo_fraction/ComplexAdv
2. promo_state_service.py:127-201 — get_campaign_balance failure still redis.set with pool_usable=false (false empty pool, not stale→M=1)
3. promo_ledger.py 90-day lookback drops campaign remaining → false AND-stop vs Owner availability law
4. promo_accounting.py FEFO applies spend to expired tranches first, inflating live remaining

MEDIUM:
5. campaign leftover fraction uses budget_after/total so M collapses
6. journal only bot WBAutoBudgetTopUp; manual WB promo deposits invisible
OBSERVED_SYMPTOM: Independent READ_ONLY review of uncommitted dirty promobonus rebuild. Six findings.
KNOWN_CONTEXT: CHAT_LABEL=SUP-PROMO-FIX-20260907; sequential max_active_findings=1; on_blocked=stop; no publication. One durable case intended to later yield sequential findings for all six review items. Intake is a raw signal; not a confirmed production bug.
STATUS: intake_recorded
LAST_ACTIVITY_AT: 2026-09-07T20:30:22Z
NEXT_ACTION: /opsx-classify-bug case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z finding=FINDING-006
DISPOSITION:
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID: ROOT-001, FINDING-002, HC-001, FINDING-003, FINDING-004, HC-FINDING-004-STALE-TEST, FINDING-005, FINDING-006
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-006/2026-09-07T20:30:22Z
RESULT_PATH:
RESIDUAL_INTAKE_ITEMS:
RESIDUAL_NOTE: Item 1 closed as ROOT-001 closed_fixed (Telegram rec-bid overlay). Item 2 closed as FINDING-002 closed_fixed with SAME_INVARIANT sibling HC-001 closed_fixed. Item 3 closed as FINDING-003 closed_false_positive Route C (90d lookback misread; leftover-usable load has no cutoff). Item 4 closed as FINDING-004 closed_fixed with SAME_INVARIANT sibling HC-FINDING-004-STALE-TEST closed_fixed / INTEGRATED. Item 5 closed as FINDING-005 closed_fixed / IMPLEMENTATION_BUG / ROUTE_A (hunt CLEAR; no HC sibling). Item 6 claimed as FINDING-006 (STATUS=claimed, CLAIM_TOKEN=CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-006/2026-09-07T20:30:22Z, OWNER_CHAT=SUP-PROMO-FIX-20260907, unclassified). Residual intake exhausted. FINDING-007 not created. RAW_REPORT preserved verbatim.
