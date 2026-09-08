FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID: FINDING-H4
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID: ROOT-001
TITLE: H4 plan_fact_stats persists overlay.plan instead of raw get_plan_data
PRODUCTION_CLASSIFICATION: confirmed production bug
RELATION_TO_ROOT: different_invariant
STATUS: backlog
CHAT_REQUIRED: false
CLAIM_PRIORITY: 4
PACKET_PATH: findings/FINDING-H4.md
OWNER_CHAT:
CLAIM_TOKEN:
PACKET_PURPOSE: backlog
INVARIANT: ClickHouse plan_fact_stats должен писать сырой PlanFactProvider.get_plan_data (unscaled PG Plan). Overlay Plan не персистится. PG Plan columns unscaled.
ORIGINAL_FINDING: H4 CH writes overlay.plan: plan_fact_stats must persist raw get_plan_data, not pre_adv.plan_data overlay. Shop-runner production loop is process_pre_adv.
EVIDENCE: WBShopDataManager._build_pre_complex_adv ставит plan_data=overlay.plan. PlanFactController.process_pre_adv пишет plan=pre_adv.plan_data в PlanFactStatDTO. Shop-runner update_plan_fact_stats → process_and_save_pre_complex_advs. process_adv путь зовёт get_plan_data, но production loop — process_pre_adv.
RUNTIME_PATH: app/modules/shop_runner/service_manager/services/plan_fact_controller/plan_fact_controller.py
CAUSAL_BOUNDARY: _build_pre_complex_adv overlay.plan → process_pre_adv → insert_plan_fact_stats
WRITE_BOUNDARY: ClickHouse default_db.plan_fact_stats plan columns
SOURCE_SNAPSHOT: intakes/INTAKE-001.md H4; results/ADJUDICATION-INTAKE-001.md
DISPOSITION:
CREATED_AT: 2026-09-07T11:50:00Z
LAST_ACTIVITY_AT: 2026-09-07T11:50:00Z
NEXT_ACTION: none

MODE: READ_ONLY
FORBIDDEN:
- do not claim this finding while ROOT-001 is active (MAX_ACTIVE_FINDINGS=1)
- do not edit production files from this packet
