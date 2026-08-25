# 02 — T2+T4 two sequential findings

```text
CASE_ID: BUGCASE-FIX-T2
FINDINGS: ROOT-001, ROOT-002
```

## Expected

```text
ACTIVE_FINDING_ID=ROOT-001 until FINDING_TERMINAL
ROOT-002 MUST NOT become ACTIVE before ROOT-001 terminal
After ROOT-001 CLOSED:
  ACTIVE_FINDING_ID cleared
  NEXT_ELIGIBLE_FINDING_ID=ROOT-002
  then claim/select ROOT-002
MISSION_COMPLETE: no until ROOT-002 also terminal
```
