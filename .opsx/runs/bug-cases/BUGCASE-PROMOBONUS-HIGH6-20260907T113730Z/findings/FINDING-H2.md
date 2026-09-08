FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID: FINDING-H2
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID: ROOT-001
TITLE: H2 campaign f denominator uses budget_after/wallet instead of top-up unit
PRODUCTION_CLASSIFICATION: confirmed production bug
RELATION_TO_ROOT: different_invariant
STATUS: promoted_to_root_case
CHAT_REQUIRED: false
CLAIM_PRIORITY: 4
PACKET_PATH: findings/FINDING-H2.md
OWNER_CHAT:
CLAIM_TOKEN:
PACKET_PURPOSE: promotion_decision
INVARIANT: Campaign leftover 200 при top-up unit 1000 обязан давать f=0.2 и M=1.25. Знаменатель — AUTO_BUDGET_TOPUP_AMOUNT (или tranche.amount), не budget_after/wallet.
ORIGINAL_FINDING: H2 campaign f denominator: campaign leftover 200 must yield M=1.25 vs the 1000 top-up unit, not remaining/wallet (budget_after). Test with remaining=200 and budget_after=5000 must fail if M is not 1.25.
EVIDENCE: campaign_ledger_from_rows берёт budget=campaign_budget_total else reference_budget из row.budget_after. PromoStateService.refresh не передаёт campaign_budget_by_adv_id (пустой dict) → знаменатель = budget_after. remaining=200 / budget_after=5000 → f=0.04, M≠1.25. Тест test_campaign_ledger_fraction_uses_remaining_not_ceiling задаёт budget_after=1000 и campaign_budget_total=1000 — не ловит дефект.
RUNTIME_PATH: app/shared/domains/wb/utils/promo_accounting.py
CAUSAL_BOUNDARY: apply_spend_fefo reference_budget=budget_after → campaign_ledger_from_rows fraction=remaining/budget → Redis effective_fraction
WRITE_BOUNDARY: Redis overlay multiplier; downstream CPO/limits scaled too low
SOURCE_SNAPSHOT: intakes/INTAKE-001.md H2; results/ADJUDICATION-INTAKE-001.md
DISPOSITION: promoted_to_root_case
CREATED_AT: 2026-09-07T11:50:00Z
LAST_ACTIVITY_AT: 2026-09-07T13:57:00Z
COMPLETED_AT: 2026-09-07T13:57:00Z
NEXT_ACTION: none
RESULT_PATH: ../BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z/CASE.md
PROMOTED_CASE_ID: BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z

MODE: READ_ONLY
FORBIDDEN:
- do not claim this finding while ROOT-001 is active (MAX_ACTIVE_FINDINGS=1)
- do not edit production files from this packet
