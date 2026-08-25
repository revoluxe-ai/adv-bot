# 10 — T11 resume after classify

```text
PRIOR: classify committed; ROUTE_STATE=AWAITING_FIX_BUG
ROUTE_TRANSITION.NEXT_COMMAND=/opsx-fix-bug
GO_TOKEN=FORBIDDEN
Chat history: lost
```

## Expected

```text
reconstruct from durable evidence
NEXT_COMMAND=/opsx-fix-bug WITHOUT GO
MUST NOT re-dispatch /opsx-classify-bug
```
