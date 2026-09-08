FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
FINDING_ID: CHILD-001
SOURCE_INTAKE_ID: INTAKE-002
PARENT_FINDING_ID: ROOT-001
TITLE: Incomplete overlay wiring — keywords/telegram/classification/menu still use base Plan
PRODUCTION_CLASSIFICATION: confirmed production bug
RELATION_TO_ROOT: same_invariant_different_path
STATUS: closed_fixed
CHAT_REQUIRED: true
CLAIM_PRIORITY: 1
PACKET_PATH: findings/CHILD-001.md
OWNER_CHAT: SUP-PROMOBONUS-P1-SSOT-20260908
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z/CHILD-001/2026-09-08T02:16:54Z
PACKET_PURPOSE: adjudication
CHILD_CHAT_RECOMMENDED: true
INVARIANT: Runtime CPO/plan overlay MUST be a single SoT via PlanFactProvider.get_effective_plan_data / promo overlay with ComplexAdv. Base Plan remains AdvSetting via get_plan_data. Consumers MUST NOT mix base and overlay.
ORIGINAL_FINDING: FINDING B — incomplete overlay wiring. Keyword GOOD/BAD in calculated_keywords_manager still uses AdvSetting max/target (base). Telegram cost-activity / is_auto_campaign_active uses get_effective_plan_data without ComplexAdv (fraction=0 → base). Watchdog/V3/shelf already see overlay. Classification and menu do not.
EVIDENCE: Owner-confirmed P1. calculated_keywords_manager reads AdvSetting max/target for GOOD/BAD. Telegram cost-activity / is_auto_campaign_active calls get_effective_plan_data without ComplexAdv so fraction=0 and overlay collapses to base. Watchdog/V3/shelf already consume overlay. Classification and menu still see base. Keyword slice thematically overlaps HIGH6 FINDING-H5 (backlog, not mutated this hop); this finding also covers telegram/classification/menu.
RUNTIME_PATH: app/modules/wb_adv_updater/calculated_keywords_manager/calculated_keywords_manager.py
CAUSAL_BOUNDARY: AdvSetting max/target → keyword GOOD/BAD; get_effective_plan_data(missing ComplexAdv) → telegram activity; classification/menu unread overlay
WRITE_BOUNDARY: Redis calculated_keywords; telegram cost-activity / is_auto_campaign_active; classification and menu surfaces
SOURCE_SNAPSHOT: intakes/INTAKE-002.md; MISSION_ID=SUP-PROMOBONUS-P1-SSOT-20260908 OWNER INTENT frozen
DISPOSITION: closed_fixed
VERDICT: closed_fixed
CREATED_AT: 2026-09-08T01:49:00Z
CLAIMED_AT: 2026-09-08T02:16:54Z
LAST_ACTIVITY_AT: 2026-09-08T02:55:00Z
COMPLETED_AT: 2026-09-08T02:55:00Z
NEXT_ACTION: none
BLOCKER:
RESULT_PATH: results/CLOSE-CHILD-001.md
EPISODE_TERMINAL: FIXED
RED_EVIDENCE_PATH: results/RED-CHILD-001.md
GREEN_EVIDENCE_PATH: results/GREEN-CHILD-001.md
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH: results/FIX-CHILD-001.md
OWNER_GO_RECEIPT_PATH: results/FIX-CHILD-001.md
TEST_ID: tests/unit/app/modules/promobonus_overlay/test_child_001_incomplete_overlay_wiring.py::test_keyword_above_target_gate_uses_effective_overlay_max_not_base_adv_setting
TEST_CONTENT_SHA256: 30d915f3b29ed2a6090cdfc65a645f2cafd1bc2939c14fa3362601bbc6e4be06
FANIN_PATH:

NEXT_COMMAND (when STATUS=available and CHAT_REQUIRED=true, pre-claim):
/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z chat_label="SUP-PROMOBONUS-P1-SSOT-20260908"

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
