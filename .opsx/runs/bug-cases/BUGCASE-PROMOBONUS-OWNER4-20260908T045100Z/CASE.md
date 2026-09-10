# Case: BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z

CASE_ID: BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z
PRIMARY_INTAKE_ID: INTAKE-001
ROOT_FINDING_ID: ROOT-001
SOURCE_TYPE: owner_report
SOURCE_REFERENCE: current user message / complete structured hunt result
PARENT_CASE_ID:
SOURCE_FINDING_ID:
ANCESTOR_CHAIN: [BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z]
DEPTH: 0
STATUS: open
CURRENT_STAGE: claimed
NEXT_ACTION: /opsx-classify-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z intake=INTAKE-001 finding=ROOT-001 claim_token=CLAIM/BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z/ROOT-001/2026-09-08T05:09:00Z
PROPOSED_INVARIANT: multiple independent root candidates; per-finding invariant extraction is deferred to adjudication
ROOT_FINGERPRINT:
CREATED_AT: 2026-09-08T04:51:00Z
UPDATED_AT: 2026-09-08T05:09:00Z
LAST_COMMAND: /opsx-materialize-bug-queue mode=hunt-result case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z

## Summary

The Owner's ordered structured hunt result is materialized as four independent
root-candidate packets. No existing root finding packet was present, and the
authoritative PRODUCTION_CLASSIFICATION and RELATION_TO_ROOT values are
preserved without repository re-analysis.

## Materialized findings

- ROOT-001: promo-ledger-upd-recovery-gap
- ROOT-002: watchdog-overlay-next-tick-lag
- ROOT-003: v3-raise-max-promo-composition
- ROOT-004: promo-cashback-alias-fingerprint

No production code or tests were changed. The next hop is claim selection in
the preserved registration order.
