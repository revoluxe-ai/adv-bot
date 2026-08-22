# 05 — T6 blocked finding stops mission

```text
ACTIVE: ROOT-001
WORKER_RESULT: BLOCKED / RECOVERY_CLASS=BLOCKED
QUEUE: ROOT-002 eligible
```

## Expected

```text
on_blocked: stop
mission stops
ROOT-002 MUST NOT start
ACTIVE_FINDING_ID remains ROOT-001 (or recorded blocked)
MISSION_COMPLETE: no
```
