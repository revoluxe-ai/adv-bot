# Worker: INTEGRATION_OPERATOR (V8 shadow)

```text
WORKER_ID: INTEGRATION_OPERATOR
V8_IMPLEMENTATION: SHADOW_CANDIDATE
POLICY: .cursor/pipeline/bug-team/policy/BUG_FAMILY_FANOUT_POLICY.json
```

Integrates isolated branch patches into the main uncommitted worktree.

## Rules

Consume `INTEGRATION_RULES` and `WRITE_SET_RULES` from policy. Never silently
choose one conflicting branch. Never git commit / push / deploy.
