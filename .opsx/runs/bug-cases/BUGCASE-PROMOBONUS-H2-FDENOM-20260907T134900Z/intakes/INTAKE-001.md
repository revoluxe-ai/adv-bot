INTAKE_RECORD

CASE_ID: BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z
INTAKE_ID: INTAKE-001
CREATED_AT: 2026-09-07T13:49:00Z
SOURCE_TYPE: promotion
SOURCE_REFERENCE: parent FINDING-H2 / .opsx/runs/bug-cases/BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z/findings/FINDING-H2.md / MISSION_ID=SUP-PROMOBONUS-FIX-20260907 TASK_ID=T15-PROMOTE-H2 DISPATCH_ID=D15
RAW_REPORT:
H2 campaign f denominator: campaign leftover 200 must yield M=1.25 vs the 1000 top-up unit, not remaining/wallet (budget_after). Test with remaining=200 and budget_after=5000 must fail if M is not 1.25.
OBSERVED_SYMPTOM: H2 campaign f denominator uses budget_after/wallet instead of top-up unit
KNOWN_CONTEXT: Promoted from parent CASE_ID=BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z SOURCE_FINDING_ID=FINDING-H2. CHAT_LABEL=SUP-PROMOBONUS-FIX-20260907. proposed_invariant and root_fingerprint supplied by /opsx-materialize-bug-queue mode=promote. H3-H6 not in this case.
STATUS: adjudicated
LAST_ACTIVITY_AT: 2026-09-07T13:57:00Z
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z chat_label="SUP-PROMOBONUS-FIX-20260907"
DISPOSITION: new_finding
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID: ROOT-001
RESULT_PATH:
