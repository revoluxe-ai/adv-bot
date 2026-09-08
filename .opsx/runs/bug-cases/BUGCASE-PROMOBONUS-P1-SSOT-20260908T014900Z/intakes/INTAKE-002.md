INTAKE_RECORD

CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
INTAKE_ID: INTAKE-002
CREATED_AT: 2026-09-08T01:49:00Z
SOURCE_TYPE: owner_confirmed
SOURCE_REFERENCE: MISSION_ID=SUP-PROMOBONUS-P1-SSOT-20260908 TASK_ID=T-MATERIALIZE-P1-001 DISPATCH_ID=D-001 invocation payload FINDING B
RAW_REPORT:
FINDING B — incomplete overlay wiring:
Keyword GOOD/BAD in calculated_keywords_manager still uses AdvSetting max/target (base). Telegram cost-activity / is_auto_campaign_active uses get_effective_plan_data without ComplexAdv (fraction=0 → base). Watchdog/V3/shelf already see overlay. Classification and menu do not.
OBSERVED_SYMPTOM: Overlay wiring incomplete — keywords/telegram/classification/menu still see base Plan while watchdog/V3/shelf see overlay
KNOWN_CONTEXT: Owner-confirmed P1 on uncommitted Promobonus overlay. Frozen intent: runtime overlay SoT is PlanFactProvider.get_effective_plan_data / promo overlay with ComplexAdv. Keyword path thematically overlaps HIGH6 FINDING-H5 backlog (not promoted; HIGH6 not mutated). Finding B is broader: telegram without ComplexAdv, classification, menu.
STATUS: adjudicated
LAST_ACTIVITY_AT: 2026-09-08T01:49:00Z
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z chat_label="SUP-PROMOBONUS-P1-SSOT-20260908"
DISPOSITION: new_finding
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID: CHILD-001
RESULT_PATH:
