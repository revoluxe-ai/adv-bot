# 24 — Repeated identical supervisor state → NO_PROGRESS (SUP-LIVE-006)

```text
iteration N and N+1:
  DURABLE_SUPERVISOR_STATE_FINGERPRINT unchanged
  NEW_DISPATCH=NO
  TERMINAL_RESULT_ACCEPTED=NO
  EXPLICIT_BLOCKED_PAUSED_OR_COMPLETED=NO
  GENUINELY_ACTIVE_WORKER_AWAITING_LEGAL_RESULT=NO
```

## Expected

Immediately:

```text
STATUS=SUPERVISOR_NO_PROGRESS
DIAGNOSTIC_STATE_DUMP=YES
FURTHER_RECONCILE_ROUTE_LOOP=FORBIDDEN
ONE_NEXT_ACTION=OWNER_DECISION_REQUIRED
```

Do not wait for heartbeat. Do not start another reconcile/route cycle.

This fixture documents a CONTRACT-PERMITTED FAILURE PATH (explicit
liveness stop), not an empirically confirmed runtime root cause of a
specific past hang.
