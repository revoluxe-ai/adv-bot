FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z
FINDING_ID: ROOT-001
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: H2 campaign f denominator uses budget_after/wallet instead of top-up unit
PRODUCTION_CLASSIFICATION: confirmed production bug
RELATION_TO_ROOT: root
STATUS: claimed
CHAT_REQUIRED: true
CLAIM_PRIORITY: 1
PACKET_PATH: findings/ROOT-001.md
OWNER_CHAT: SUP-PROMOBONUS-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z/ROOT-001/2026-09-07T14:02:09Z
PACKET_PURPOSE: adjudication
INVARIANT: Campaign leftover 200 при top-up unit 1000 обязан давать f=0.2 и M=1.25. Знаменатель — AUTO_BUDGET_TOPUP_AMOUNT (или tranche.amount), не budget_after/wallet.
ORIGINAL_FINDING: H2 campaign f denominator: campaign leftover 200 must yield M=1.25 vs the 1000 top-up unit, not remaining/wallet (budget_after). Test with remaining=200 and budget_after=5000 must fail if M is not 1.25.
EVIDENCE: campaign_ledger_from_rows берёт budget=campaign_budget_total else reference_budget из row.budget_after. PromoStateService.refresh не передаёт campaign_budget_by_adv_id (пустой dict) → знаменатель = budget_after. remaining=200 / budget_after=5000 → f=0.04, M≠1.25. Тест test_campaign_ledger_fraction_uses_remaining_not_ceiling задаёт budget_after=1000 и campaign_budget_total=1000 — не ловит дефект.
RUNTIME_PATH: app/shared/domains/wb/utils/promo_accounting.py
CAUSAL_BOUNDARY: apply_spend_fefo reference_budget=budget_after → campaign_ledger_from_rows fraction=remaining/budget → Redis effective_fraction
WRITE_BOUNDARY: Redis overlay multiplier; downstream CPO/limits scaled too low
SOURCE_SNAPSHOT: parent findings/FINDING-H2.md; parent intakes/INTAKE-001.md H2; this intakes/INTAKE-001.md
DISPOSITION:
CREATED_AT: 2026-09-07T13:57:00Z
CLAIMED_AT: 2026-09-07T14:02:09Z
LAST_ACTIVITY_AT: 2026-09-07T14:02:09Z
COMPLETED_AT:
NEXT_ACTION: classify_before_impl_route
BLOCKER:
RESULT_PATH:
EPISODE_TERMINAL:
RED_EVIDENCE_PATH:
GREEN_EVIDENCE_PATH:
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH:
TEST_ID:
TEST_CONTENT_SHA256:
FANIN_PATH:

NEXT_COMMAND:
/opsx-classify-bug case=BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z intake=INTAKE-001 finding=ROOT-001 claim_token=CLAIM/BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z/ROOT-001/2026-09-07T14:02:09Z

MODE:
READ_ONLY

FORBIDDEN:
- do not edit production files
- do not use GO
- do not claim a second finding
- do not open other chats
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=
- do not start FINDING-H3..H6
- do not implement H2 in this materialize hop
