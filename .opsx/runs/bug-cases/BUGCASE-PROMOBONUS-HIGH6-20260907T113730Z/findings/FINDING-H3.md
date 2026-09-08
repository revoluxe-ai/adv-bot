FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID: FINDING-H3
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID: ROOT-001
TITLE: H3 one-tick overlay lag — raised CPO/limits after pool and leftover exhausted
PRODUCTION_CLASSIFICATION: confirmed production bug
RELATION_TO_ROOT: different_invariant
STATUS: backlog
CHAT_REQUIRED: false
CLAIM_PRIORITY: 4
PACKET_PATH: findings/FINDING-H3.md
OWNER_CHAT:
CLAIM_TOKEN:
PACKET_PURPOSE: backlog
INVARIANT: На тике, где pool и campaign remaining оба исчерпаны, overlay обязан быть fail-closed M=1. Refresh-after-DTO-build с лагом в один тик недопустим, если текущий тик продолжает raised CPO/limits/budget.
ORIGINAL_FINDING: H3 one-tick overlay lag: overlay used on a tick must not keep raised CPO/limits after both pool and campaign remaining are exhausted. Refresh-after-DTO-build is not acceptable unless fail-closed M=1.
EVIDENCE: auto_budget_watchdog строит ComplexAdv из Redis overlay, затем refresh_promo_state пишет свежий snapshot, но намеренно не обновляет DTO. Docstring в AutoBudgetService.refresh_promo_state и watchdog это фиксирует. Текущий тик использует stale PromoAutoBudget/PropoSearchBudget для top-up.
RUNTIME_PATH: app/modules/shop_runner/service_manager/manager.py
CAUSAL_BOUNDARY: get_complex_advs (stale overlay) → refresh_promo_state (new Redis, DTO unchanged) → candidates use adv.auto_budget_daily_limit from stale overlay
WRITE_BOUNDARY: WB auto-budget top-up amount / activity limits on the exhaustion tick
SOURCE_SNAPSHOT: intakes/INTAKE-001.md H3; results/ADJUDICATION-INTAKE-001.md
DISPOSITION:
CREATED_AT: 2026-09-07T11:50:00Z
LAST_ACTIVITY_AT: 2026-09-07T11:50:00Z
NEXT_ACTION: none

MODE: READ_ONLY
FORBIDDEN:
- do not claim this finding while ROOT-001 is active (MAX_ACTIVE_FINDINGS=1)
- do not edit production files from this packet
