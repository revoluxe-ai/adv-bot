# 23 — No active worker + unfinished mission (SUP-LIVE-005)

```text
MISSION_STATUS=ACTIVE
ALL_TASKS_TERMINAL=NO
READY tasks exist (or BLOCKED/PENDING remaining)
GENUINELY_ACTIVE_WORKER_AWAITING_LEGAL_RESULT=NO
PRIMARY_TASK_HANDLE: none / cleared
```

## Expected

Supervisor MUST in this iteration:

```text
DISPATCH next READY task
OR EXPLICIT_BLOCK (BLOCKED | PAUSED | listed terminal)
OR complete mission if remaining work is actually terminal
```

Heartbeat wait: FORBIDDEN.

## Negative

```text
unfinished mission + no active worker + no dispatch + no explicit block
→ SUPERVISOR_NO_PROGRESS (not hang-wait)
```
