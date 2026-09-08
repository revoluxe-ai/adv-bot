# CASE: BUGCASE-PROMOBONUS-P0-LEFTOVER-20260908T030401Z

CASE_ID: BUGCASE-PROMOBONUS-P0-LEFTOVER-20260908T030401Z
PRIMARY_INTAKE_ID: INTAKE-001
ROOT_FINDING_ID: P0-001
SOURCE_TYPE: owner_confirmed
SOURCE_REFERENCE: MISSION_ID=SUP-PROMOBONUS-P1-SSOT-20260908 TASK_ID=T-MAT-P0-LEFTOVER DISPATCH_ID=D-019 WORKER_ID=WEX_MAT_P0_001
PARENT_CASE_ID:
SOURCE_FINDING_ID:
ANCESTOR_CHAIN: [BUGCASE-PROMOBONUS-P0-LEFTOVER-20260908T030401Z]
DEPTH: 0
STATUS: closed
CURRENT_STAGE: closed_fixed_verified
NEXT_ACTION: (none — Owner reviews uncommitted diff)
PROPOSED_INVARIANT: While usable promo exists on campaign leftover OR common pool, overlay fraction f MUST come from package percent (e.g. 50% → f=0.5, multiplier=2). Elevated spend remaining = leftover/f then STOP. MUST NOT use leftover/last_tranche amount as f.
ROOT_FINGERPRINT: package_percent_overlay_fraction|elevated_spend_leftover_over_f_stop|apply_spend_fefo_not_leftover_over_last_tranche|promo_accelerator_not_plan_columns|raise_plan_on_promobonuses_default_false
CREATED_AT: 2026-09-08T03:04:01Z
UPDATED_AT: 2026-09-08T03:25:45Z
LAST_COMMAND: /opsx-bug-team
FIRST_CLAIM_CANDIDATE: P0-001
ACTIVE_FINDING_ID: P0-001
CASE_CLOSED: yes
MISSION_COMPLETE: no

## Summary

Owner-confirmed P0 defect on promo leftover fraction semantics in apply_spend_fefo. Distinct invariant from closed P1 overlay SSOT case (BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z). P0-001 available CHAT_REQUIRED=true. No production edits this hop. RaisePlanOnPromobonuses not enabled.

## Owner intent (frozen)

Package percent drives overlay while usable promo exists. Elevated spend remaining = leftover/f then STOP. Reject leftover/last_topup.amount as f. Promobonus is spend accelerator; base Plan in PG unscaled; overlay runtime-only; CH stores base Plan only (P1 closed — no regression).

## Fingerprint

- forbidden_effect: overlay multiplier explosion (~1e6) from f≈1 when multi-tranche leftover summed over last tranche amount; persisting scaled Plan columns via RaisePlanOnPromobonuses
- causal_boundary: apply_spend_fefo and helpers deriving promo fraction from leftover vs last tranche amount → overlay multiplier consumers
- write_boundary: runtime overlay fraction/multiplier only; PG base Plan; CH plan_fact base Plan
- production_state: uncommitted promobonus overlay work; RaisePlanOnPromobonuses default false
- invariant: package_percent_overlay_fraction; elevated_spend_leftover_over_f_stop; not leftover_over_last_tranche
- MATCH vs P1 SSOT fingerprint: false (different invariant — P1 is CH/overlay SoT wiring)
- MATCH vs REBUILD FINDING-005 leftover-over-tranche fingerprint: related symptom, Owner rejected that formula — this case tracks corrected package-percent semantics

## Materializer boundaries

PRODUCTION_CLASSIFICATION_SET: true (owner-confirmed; not reclassified by this command)
CREATE_ROOT_FINDING: true (mode=update after intake)
MATERIALIZE_COUNT: 1
EXISTING_ROOT: true
P1_MUTATED: false
P1_REOPENED: false

CASE_STATUS: CLOSED
TERMINAL_STATUS: CLOSED_FIXED_VERIFIED
