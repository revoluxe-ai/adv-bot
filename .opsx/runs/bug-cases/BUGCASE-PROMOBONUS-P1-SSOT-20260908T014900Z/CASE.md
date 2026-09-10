# CASE: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z

CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
PRIMARY_INTAKE_ID: INTAKE-001
ROOT_FINDING_ID: ROOT-001
SOURCE_TYPE: owner_confirmed
SOURCE_REFERENCE: MISSION_ID=SUP-PROMOBONUS-P1-SSOT-20260908 TASK_ID=T-MATERIALIZE-P1-001 DISPATCH_ID=D-001 WORKER_ID=WEX_MATERIALIZE_P1_SSOT
PARENT_CASE_ID:
SOURCE_FINDING_ID:
ANCESTOR_CHAIN: [BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z]
DEPTH: 0
STATUS: closed
CURRENT_STAGE: all_findings_closed_fixed
NEXT_ACTION: /opsx-materialize-bug-queue mode=fanin_assemble case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
PROPOSED_INVARIANT: ClickHouse plan_fact history MUST store base Plan only (PlanFactProvider.get_plan_data / AdvSetting). Runtime CPO/plan overlay MUST be a single SoT via PlanFactProvider.get_effective_plan_data / promo overlay with ComplexAdv.
ROOT_FINGERPRINT: ch_plan_fact_stores_base_plan_only|runtime_overlay_ssot_get_effective_plan_data|process_pre_adv_writes_pre_adv.plan_data|consumers_must_pass_complexadv
CREATED_AT: 2026-09-08T01:49:00Z
UPDATED_AT: 2026-09-08T02:55:00Z
LAST_COMMAND: /opsx-materialize-bug-queue mode=update close=fixed
FIRST_CLAIM_CANDIDATE: none
ACTIVE_FINDING_ID:
CASE_CLOSED: yes
MISSION_COMPLETE: no

## Summary

Owner-confirmed P1 pair on uncommitted Promobonus overlay work. ROOT-001 (CH overlay write) and CHILD-001 (incomplete overlay wiring) both closed_fixed CLOSED_GREEN after RED/GO/GREEN chains. Case queue exhausted; OPEN_FINDINGS=0. ROOT-001 not reopened. No GO on this hop.

## Owner intent (frozen)

Single source of truth for runtime CPO/plan overlay. Base Plan stays in AdvSetting via PlanFactProvider.get_plan_data. Runtime overlay is PlanFactProvider.get_effective_plan_data / promo overlay. ClickHouse plan_fact history MUST store base Plan only.

## Fingerprint

- forbidden_effect: CH stores scaled PromoMaxCPO/PromoTargetCPO as persisted Plan; runtime consumers mix base AdvSetting CPO and overlay
- causal_boundary: WBShopDataManager._build_pre_complex_adv overlay.plan → PlanFactController.process_pre_adv; calculated_keywords_manager AdvSetting CPO; telegram get_effective_plan_data without ComplexAdv
- write_boundary: ClickHouse default_db.plan_fact_stats plan columns; Redis calculated_keywords; telegram cost-activity / is_auto_campaign_active
- production_state: uncommitted promobonus overlay; RaisePlanOnPromobonuses not enabled this hop
- invariant: ch_plan_fact_stores_base_plan_only; runtime_overlay_ssot_get_effective_plan_data
- MATCH vs HIGH6 leftover fingerprint: false (not duplicate_ancestor)

## Materializer boundaries

PRODUCTION_CLASSIFICATION_SET: true (owner-confirmed; not reclassified by this command)
CREATE_ROOT_FINDING: true (mode=update after intake)
MATERIALIZE_COUNT: 2
EXISTING_ROOT: true
HIGH6_MUTATED: false
