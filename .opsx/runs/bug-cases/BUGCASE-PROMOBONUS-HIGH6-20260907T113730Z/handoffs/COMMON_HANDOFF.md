COMMON_HANDOFF

CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
ACTIVE_FINDING_ID:
STATUS: none_available
CLAIM_TOKEN:

Paste into a new chat:

/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z chat_label="SUP-PROMOBONUS-FIX-20260907"

H2 continuation (promoted descendant):

/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z chat_label="SUP-PROMOBONUS-FIX-20260907"

Rules:
- no finding ID in this common handoff
- ROOT-001 is closed_fixed CLOSED_GREEN; do not re-claim
- FINDING-H2 STATUS=promoted_to_root_case; work continues on BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z
- FINDING-H3..H6 remain backlog with CHAT_REQUIRED=false (not claimable)
- do not add GO
- do not edit production/app
- do not invent CLAIM_TOKEN
- do not start FINDING-H3..H6
- do not claim ROOT-001 of BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
