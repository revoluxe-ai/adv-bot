INTAKE_RECORD

CASE_ID: BUGCASE-PROMOBONUS-P0-LEFTOVER-20260908T030401Z
INTAKE_ID: INTAKE-001
CREATED_AT: 2026-09-08T03:04:01Z
SOURCE_TYPE: owner_confirmed
SOURCE_REFERENCE: MISSION_ID=SUP-PROMOBONUS-P1-SSOT-20260908 TASK_ID=T-MAT-P0-LEFTOVER DISPATCH_ID=D-019 WORKER_ID=WEX_MAT_P0_001 invocation payload
RAW_REPORT:
P0 DEFECT (Owner-locked semantics):
- File: app/shared/domains/wb/utils/promo_accounting.py function apply_spend_fefo (and any helper that derives promo fraction / overlay multiplier from leftover vs last tranche amount)
- Current wrong behavior: sums all live leftover promo into numerator; denominator reference_budget overwritten to LAST live tranche amount
- Two success top-ups of 1000 with 500 promo each, spend 0 → remaining 1000 / last 1000 → f≈1 → promo_fraction_from_amounts can cap near 1 → overlay M explodes (~1e6)
- Tests today only cover single tranche 200/1000 → 1.25× (tests/unit/wb/utils/test_promo_accounting.py) — insufficient
- Owner REJECTED leftover/last_topup.amount as f: «замудренная логика»
- CORRECT: while usable promo exists on campaign leftover OR common pool, raise CPO/budgets by PACKAGE PERCENT (50% → 2× i.e. f=0.5, multiplier=2)
- Elevated spend remaining = leftover / f then STOP
  Example: leftover 200 promo at 50% → elevated remaining = 200/0.5 = 400 then STOP (200 promo + 200 ordinary)
- Promobonus is spend accelerator, not extra stored Plan columns
- Flag RaisePlanOnPromobonuses stays default false / not enabled
- Base Plan in PG unscaled; overlay runtime-only; CH plan_fact stores base Plan (P1 already closed — do not regress)
OBSERVED_SYMPTOM: apply_spend_fefo derives f from summed leftover over last tranche amount; multi-tranche case yields f≈1 and overlay multiplier explosion (~1e6)
KNOWN_CONTEXT: Owner ordered after P1 KEEP + independent review. NEW case distinct from P1 overlay SSOT (BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z ROOT-001/CHILD-001 closed_fixed — do not reopen). RaisePlanOnPromobonuses not enabled. Materialize only; no production rewrite this hop.
STATUS: adjudicated
LAST_ACTIVITY_AT: 2026-09-08T03:04:01Z
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-P0-LEFTOVER-20260908T030401Z chat_label="SUP-PROMOBONUS-P1-SSOT-20260908"
DISPOSITION: new_finding
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID: P0-001
RESULT_PATH:
