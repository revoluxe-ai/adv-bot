FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
FINDING_ID: ROOT-001
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: CH overlay write — plan_fact_stats persists overlay.plan instead of base Plan
PRODUCTION_CLASSIFICATION: confirmed production bug
RELATION_TO_ROOT: root
STATUS: closed_fixed
CHAT_REQUIRED: true
CLAIM_PRIORITY: 1
PACKET_PATH: findings/ROOT-001.md
OWNER_CHAT: SUP-PROMOBONUS-P1-SSOT-20260908
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z/ROOT-001/2026-09-08T01:54:19Z
PACKET_PURPOSE: red_authoring
INVARIANT: ClickHouse plan_fact history MUST store base Plan only (PlanFactProvider.get_plan_data / AdvSetting). Overlay Plan (PromoMaxCPO/PromoTargetCPO) MUST NOT be persisted as plan columns.
ORIGINAL_FINDING: FINDING A — CH overlay write. Production CoroutinesManager.update_plan_fact_stats → PlanFactManager.process_and_save_pre_complex_advs → PlanFactController.process_pre_adv writes plan=pre_adv.plan_data. WBShopDataManager._build_pre_complex_adv sets plan_data = overlay.plan. So CH stores scaled PromoMaxCPO/PromoTargetCPO as if they were the persisted Plan. Test test_get_plan_data_stays_raw does not cover this path.
EVIDENCE: Owner-confirmed P1. Production write path is process_pre_adv (not process_adv). _build_pre_complex_adv assigns plan_data = overlay.plan. process_pre_adv writes plan=pre_adv.plan_data into PlanFactStatDTO / insert_plan_fact_stats. test_get_plan_data_stays_raw covers get_plan_data raw read, not this CH write path. Thematic overlap with HIGH6 FINDING-H4 (backlog, not mutated this hop).
RUNTIME_PATH: app/modules/shop_runner/service_manager/services/plan_fact_controller/plan_fact_controller.py
CAUSAL_BOUNDARY: WBShopDataManager._build_pre_complex_adv overlay.plan → PlanFactController.process_pre_adv → insert_plan_fact_stats
WRITE_BOUNDARY: ClickHouse default_db.plan_fact_stats plan columns
SOURCE_SNAPSHOT: intakes/INTAKE-001.md; results/FORENSICS-ROOT-001.md; MISSION_ID=SUP-PROMOBONUS-P1-SSOT-20260908 OWNER INTENT frozen
DISPOSITION: closed_fixed
CREATED_AT: 2026-09-08T01:49:00Z
CLAIMED_AT: 2026-09-08T01:54:19Z
LAST_ACTIVITY_AT: 2026-09-08T02:25:00Z
COMPLETED_AT: 2026-09-08T02:25:00Z
NEXT_ACTION: none
BLOCKER:
RESULT_PATH: results/CLOSE-ROOT-001.md
EPISODE_TERMINAL: FIXED
FINDING_TERMINAL_KIND: CLOSED_GREEN
RED_EVIDENCE_PATH: results/RED-ROOT-001.md
GREEN_EVIDENCE_PATH: results/GREEN-ROOT-001.md
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH: results/FIX-ROOT-001.md
TEST_ID: tests/unit/app/modules/shop_runner/services/plan_fact_controller/test_process_pre_adv_plan_source.py::test_process_pre_adv_persists_base_plan_not_overlay_on_write_boundary
TEST_CONTENT_SHA256: 9de02d7aa5a9ce0dc4fe20a87d8bea8f80d4ac6ce84df44c5252f63d6938f0e7
FANIN_PATH:

NEXT_COMMAND (when STATUS=available and CHAT_REQUIRED=true, pre-claim):
/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z chat_label="SUP-PROMOBONUS-P1-SSOT-20260908"

VERDICT: fix_now
RUNTIME_REACHABLE: yes
DEAD_OR_LEGACY: no
WRITE_BOUNDARY_REACHABLE: yes
CURRENT_CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A
ROUTE_RECONCILIATION: MATCH
FOLLOW_UP_SCOPE: none
AUTO_MATERIALIZE: false

ENTRYPOINT_CHAIN:
- shop-runner wb_shop.py TaskGroup → CoroutinesManager.update_plan_fact_stats (5 min) → WBShopDataManager.get_pre_complex_advs → PlanFactManager.process_and_save_pre_complex_advs → PlanFactController.process_pre_adv → insert_plan_fact_stats
- WBShopDataManager._build_pre_complex_adv: overlay_for_adv → plan_data=overlay.plan (defect upstream of write)

MINIMAL_FIX_PLAN:
- files allowed: app/modules/shop_runner/service_manager/services/plan_fact_controller/plan_fact_controller.py (preferred: process_pre_adv uses PlanFactProvider.get_plan_data like process_adv); app/modules/shop_runner/service_manager/wb_shop_data_manager/wb_shop_data_manager.py (optional seed semantics)
- files forbidden: tests (RED via /opsx-test); CHILD-001 consumers; openspec/**; RaisePlanOnPromobonuses enablement; leftover/P0 mix; HIGH6 mutation
- exact behavior change: CH plan_fact_stats plan columns receive base Plan from get_plan_data, not overlay.plan from pre_adv.plan_data
- regression: unit test that process_pre_adv persists base Plan when overlay active on PreComplexAdv

MODE:
READ_ONLY

FORBIDDEN:
- do not edit production files
- do not use GO
- do not claim a second finding
- do not open other chats
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=
- do not enable RaisePlanOnPromobonuses
- do not change leftover/P0 mix formula
- do not mutate HIGH6 or other cases
- do not implement product fixes from this materialize hop
