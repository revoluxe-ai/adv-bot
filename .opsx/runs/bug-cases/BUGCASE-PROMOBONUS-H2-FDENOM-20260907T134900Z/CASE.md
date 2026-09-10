# CASE: BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z

CASE_ID: BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z
PRIMARY_INTAKE_ID: INTAKE-001
ROOT_FINDING_ID: ROOT-001
SOURCE_TYPE: promotion
SOURCE_REFERENCE: parent FINDING-H2 / BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z / MISSION_ID=SUP-PROMOBONUS-FIX-20260907 TASK_ID=T15-PROMOTE-H2 DISPATCH_ID=D15
PARENT_CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
SOURCE_FINDING_ID: FINDING-H2
ANCESTOR_CHAIN: [BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z, BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z]
DEPTH: 1
STATUS: open
CURRENT_STAGE: claimed
NEXT_ACTION: /opsx-classify-bug case=BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z intake=INTAKE-001 finding=ROOT-001
PROPOSED_INVARIANT: Campaign leftover 200 при top-up unit 1000 обязан давать f=0.2 и M=1.25. Знаменатель — AUTO_BUDGET_TOPUP_AMOUNT (или tranche.amount), не budget_after/wallet.
ROOT_FINGERPRINT: campaign_f_must_use_topup_unit_not_budget_after|apply_spend_fefo_reference_budget|redis_overlay_multiplier|promo_state_refresh_empty_campaign_budget|leftover_200_over_topup_1000_f_0.2_M_1.25
CREATED_AT: 2026-09-07T13:49:00Z
UPDATED_AT: 2026-09-07T14:02:09Z
LAST_COMMAND: /opsx-claim-next-bug
FIRST_CLAIM_CANDIDATE: ROOT-001
ACTIVE_FINDING_ID: ROOT-001
CASE_CLOSED: no
MISSION_COMPLETE: no

## Summary

Promoted from parent BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z FINDING-H2 (different_invariant). Ancestor fingerprint mismatch confirmed (not duplicate_ancestor). New root ROOT-001 is claimable. DEPTH=1 (parent DEPTH=0 + 1). CONFIRM_DEEP_PROMOTE not required. H3–H6 not promoted this hop.

## Fingerprint check

- ancestor BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z ROOT_FINGERPRINT: leftover_usable_must_keep_overlay_on|load_campaign_ledgers_90d_cutoff|redis_promo_overlay_usable|raise_plan_on_promobonuses_runtime
- this case ROOT_FINGERPRINT: campaign_f_must_use_topup_unit_not_budget_after|apply_spend_fefo_reference_budget|redis_overlay_multiplier|promo_state_refresh_empty_campaign_budget|leftover_200_over_topup_1000_f_0.2_M_1.25
- MATCH: false
