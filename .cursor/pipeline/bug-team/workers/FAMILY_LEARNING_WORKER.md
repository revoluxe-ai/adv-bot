# Worker: FAMILY_LEARNING_WORKER (V8/V9 shadow)

```text
WORKER_ID: FAMILY_LEARNING_WORKER
ACTIVATION_STATUS: SHADOW_V8
POLICY: .cursor/pipeline/bug-team/policy/BUG_FAMILY_FANOUT_POLICY.json
```

Writes `family/LEARNING_PACKET.json` only when family fan-in is
`READY_FOR_FAMILY_CLOSURE` (BF-V9-003).
