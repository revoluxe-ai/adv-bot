INTAKE_RECORD

CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
INTAKE_ID: INTAKE-001
CREATED_AT: 2026-09-07T11:37:30Z
SOURCE_TYPE: independent_review
SOURCE_REFERENCE: invocation payload / MISSION_ID=SUP-PROMOBONUS-FIX-20260907 TASK_ID=T03-MATERIALIZE-INTAKE DISPATCH_ID=D03 ATTEMPT=1
RAW_REPORT:
Independent dirty-tree review of uncommitted promobonus rebuild. Six HIGH defects. No production migration. No commit/push/PR. No A1 enablement.

H1 90d lookback false-stop: 90-day ledger window can turn overlay OFF while promo leftover still sits on the campaign (false AND-stop when pool=0).

H2 campaign f denominator: campaign leftover 200 must yield M=1.25 vs the 1000 top-up unit, not remaining/wallet (budget_after). Test with remaining=200 and budget_after=5000 must fail if M is not 1.25.

H3 one-tick overlay lag: overlay used on a tick must not keep raised CPO/limits after both pool and campaign remaining are exhausted. Refresh-after-DTO-build is not acceptable unless fail-closed M=1.

H4 CH writes overlay.plan: plan_fact_stats must persist raw get_plan_data, not pre_adv.plan_data overlay. Shop-runner production loop is process_pre_adv.

H5 keyword resolve wipes overlay CPO: keyword GOOD/BAD resolve must use overlay CPO (PromoTargetCPO / PromoMaxCPO), not AdvSetting.target/max, when raise_plan_on_promobonuses is on.

H6 expired cashback shadows live package: pick_cashback_for_topup must skip expired packages and pick the next live FEFO row.

Keep labels literal including PropoSearchBudget. Keep PG Plan columns unscaled.
OBSERVED_SYMPTOM: Independent dirty-tree review of uncommitted promobonus rebuild. Six HIGH defects. No production migration. No commit/push/PR. No A1 enablement.
KNOWN_CONTEXT: MISSION_ID=SUP-PROMOBONUS-FIX-20260907; TASK_ID=T03-MATERIALIZE-INTAKE; DISPATCH_ID=D03; CHAT_LABEL=SUP-PROMOBONUS-FIX-20260907. New case required; not attached to BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z. create_root_finding=false. Intake is a raw signal; not a confirmed production bug; does not assert how many separate findings exist.
STATUS: adjudicated
LAST_ACTIVITY_AT: 2026-09-07T12:30:20Z
NEXT_ACTION: /opsx-test case=BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z finding=ROOT-001 verify
DISPOSITION: new_finding
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID: ROOT-001
RESULT_PATH: results/ADJUDICATION-INTAKE-001.md
