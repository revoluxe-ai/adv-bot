# 09 — T10 stale/invalid claim

```text
ACTIVE: ROOT-001
CLAIM_TOKEN durable ≠ provided / claim expired / STATUS not claimed
NEXT would be writer (/opsx-fix-bug GO or scoped write)
```

## Expected

```text
no writer dispatch
PAUSED or BLOCKED (claim gate)
MISSION_COMPLETE: no
```
