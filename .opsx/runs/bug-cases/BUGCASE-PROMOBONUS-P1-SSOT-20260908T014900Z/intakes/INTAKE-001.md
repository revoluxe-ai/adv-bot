INTAKE_RECORD

CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
INTAKE_ID: INTAKE-001
CREATED_AT: 2026-09-08T01:49:00Z
SOURCE_TYPE: owner_confirmed
SOURCE_REFERENCE: MISSION_ID=SUP-PROMOBONUS-P1-SSOT-20260908 TASK_ID=T-MATERIALIZE-P1-001 DISPATCH_ID=D-001 invocation payload FINDING A
RAW_REPORT:
FINDING A — CH overlay write:
Production CoroutinesManager.update_plan_fact_stats → PlanFactManager.process_and_save_pre_complex_advs → PlanFactController.process_pre_adv writes plan=pre_adv.plan_data. WBShopDataManager._build_pre_complex_adv sets plan_data = overlay.plan. So CH stores scaled PromoMaxCPO/PromoTargetCPO as if they were the persisted Plan. Test test_get_plan_data_stays_raw does not cover this path.
OBSERVED_SYMPTOM: ClickHouse plan_fact_stats persists overlay.plan (PromoMaxCPO/PromoTargetCPO) as if it were the base Plan
KNOWN_CONTEXT: Owner-confirmed P1 on uncommitted Promobonus overlay. Frozen intent: CH plan_fact history MUST store base Plan only. Corresponds thematically to HIGH6 FINDING-H4 backlog (not promoted; HIGH6 not mutated). Test test_get_plan_data_stays_raw does not cover process_pre_adv write path.
STATUS: adjudicated
LAST_ACTIVITY_AT: 2026-09-08T01:49:00Z
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z chat_label="SUP-PROMOBONUS-P1-SSOT-20260908"
DISPOSITION: new_finding
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID: ROOT-001
RESULT_PATH:
