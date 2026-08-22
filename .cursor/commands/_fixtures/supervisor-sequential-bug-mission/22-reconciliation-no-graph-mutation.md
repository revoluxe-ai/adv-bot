# 22 — Reconciliation without graph mutation cannot loop (SUP-LIVE-004)

```text
WRITER_RETURNED
WRITE_SCOPE_RECONCILED already computed for this snapshot
DURABLE_SUPERVISOR_STATE_FINGERPRINT unchanged
no TASK_ADDED / DEPENDENCY_* / CORRECTION / REAUDIT graph mutation
```

## Expected

```text
FURTHER_RECONCILE_ROUTE_LOOP=FORBIDDEN
do not re-enter: reconcile → route → reconcile
next must be DISPATCH | EXPLICIT_BLOCK | SUPERVISOR_NO_PROGRESS
  (or no-op that immediately produces one of those)
```

## Negative

A second full post-write inventory / routing refresh / scenario re-audit
on the same fingerprint is a liveness violation.
