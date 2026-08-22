# 20 — Completed worker cannot remain RUNNING (SUP-LIVE-002)

```text
TASK_ID: T-1
ATTEMPT: 1
PRIMARY_TASK_HANDLE: handle-abc  (recorded at launch)
WORKER: terminal success envelope, IDENTITY_VALID
RESULT_VALIDATION: ACCEPTED
```

## Expected

```text
T-1 STATUS ≠ RUNNING
T-1 STATUS = COMPLETED
PRIMARY_TASK_HANDLE no longer an awaitable active handle
heartbeat wait: FORBIDDEN
```

## Negative

Leaving T-1 `RUNNING` after accepted terminal result is a contract
violation even if optional `PLATFORM_TASK_ID` / `PLATFORM_AGENT_ID`
were never present.
