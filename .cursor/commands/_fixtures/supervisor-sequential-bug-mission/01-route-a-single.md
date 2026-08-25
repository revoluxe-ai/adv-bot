# 01 — T1 Route A single finding

```text
CASE_ID: BUGCASE-FIX-T1
FINDINGS: ROOT-001
POLICY: sequential max_active=1
```

## Envelopes (ordered)

1. claim → ACTIVE_FINDING=ROOT-001; NEXT=/opsx-classify-bug
2. classify ROUTE_TRANSITION: NEXT=/opsx-fix-bug; GO_TOKEN=FORBIDDEN; MISSION_COMPLETE=no; FINDING_TERMINAL=no
3. fix-bug (no GO) fix_now → NEXT=/opsx-test; MISSION_COMPLETE=no
4. test RED_CONFIRMED → NEXT=/opsx-fix-bug GO (Owner); MISSION_COMPLETE=no
5. fix-bug GO applied → NEXT=/opsx-test verify
6. GREEN + close evidence → FINDING_TERMINAL=yes CLOSED_GREEN; clear ACTIVE

## Expected

```text
RECOVERY: ADVANCE each hop
MISSION_COMPLETE: yes only after step 6 + queue empty
NO_LLM_ROUTE_PLANNING: yes
```
