# 14 — T15 deterministic replay

```text
Same durable ROUTE_STATE + same verified ROUTE_TRANSITION envelopes
Replay supervisor reducer twice
```

## Expected

```text
identical reduced state
identical NEXT_COMMAND / NEXT_ARGS
no duplicate committed transition dispatch
```
