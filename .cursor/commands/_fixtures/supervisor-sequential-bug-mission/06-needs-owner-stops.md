# 06 — T7 NEEDS_OWNER stops mission

```text
ACTIVE: ROOT-001
RECOVERY_CLASS: NEEDS_OWNER
QUEUE: ROOT-002 eligible
```

## Expected

```text
on_needs_owner: stop
mission stops
ROOT-002 MUST NOT start
MISSION_COMPLETE: no
```
