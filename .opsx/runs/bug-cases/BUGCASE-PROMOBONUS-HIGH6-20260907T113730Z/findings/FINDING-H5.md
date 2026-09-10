FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID: FINDING-H5
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID: ROOT-001
TITLE: H5 keyword GOOD/BAD resolve wipes overlay CPO via AdvSetting/CH
PRODUCTION_CLASSIFICATION: confirmed production bug
RELATION_TO_ROOT: different_invariant
STATUS: backlog
CHAT_REQUIRED: false
CLAIM_PRIORITY: 4
PACKET_PATH: findings/FINDING-H5.md
OWNER_CHAT:
CLAIM_TOKEN:
PACKET_PURPOSE: backlog
INVARIANT: При raise_plan_on_promobonuses=on keyword GOOD/BAD / above-target cooldown обязан сравнивать CPO с PromoTargetCPO / PromoMaxCPO overlay, не с AdvSetting.target_price_for_order / max_price_for_order.
ORIGINAL_FINDING: H5 keyword resolve wipes overlay CPO: keyword GOOD/BAD resolve must use overlay CPO (PromoTargetCPO / PromoMaxCPO), not AdvSetting.target/max, when raise_plan_on_promobonuses is on.
EVIDENCE: CalculatedKeywordsManager.__get_calculated_keywords читает _plan_t/_plan_m с adv_setting.target/max, затем PlanFactReader.get_latest_plan_fact может перезаписать resolved_target_cost через resolve_target_cost(_plan_o, _plan_t, _plan_m, fact) — unscaled. _apply_above_target_cooldown использует этот resolved_target_cost для GOOD/BAD. Комментарий «Do not query ClickHouse again» противоречит коду.
RUNTIME_PATH: app/modules/wb_adv_updater/calculated_keywords_manager/calculated_keywords_manager.py
CAUSAL_BOUNDARY: __get_calculated_keywords CH override from AdvSetting CPO → _apply_above_target_cooldown → KeywordStatus GOOD/BAD
WRITE_BOUNDARY: Redis calculated_keywords + downstream minus-phrase / bid structural mutations
SOURCE_SNAPSHOT: intakes/INTAKE-001.md H5; results/ADJUDICATION-INTAKE-001.md
DISPOSITION:
CREATED_AT: 2026-09-07T11:50:00Z
LAST_ACTIVITY_AT: 2026-09-07T11:50:00Z
NEXT_ACTION: none

MODE: READ_ONLY
FORBIDDEN:
- do not claim this finding while ROOT-001 is active (MAX_ACTIVE_FINDINGS=1)
- do not edit production files from this packet
