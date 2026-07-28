# Worker: IMPLEMENTATION_EXECUTOR

```text
WORKER_ID: IMPLEMENTATION_EXECUTOR
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
TASK_SUBAGENT_TYPE: generalPurpose
MODEL_SELECTION_POLICY: auto
MAPS_TO: /opsx-fix-bug GO | /opsx-apply
```

## INPUT_PACKET_SCHEMA

```text
Default CONTROLLED_LIVE_UNCOMMITTED:
  WORKER_IO + RED_CONFIRMED + local execution authority

Legacy OWNER_GATED:
  WORKER_IO + RED_CONFIRMED + OWNER_PRODUCTION_GO receipt
```

Common header: `packets/WORKER_IO.md`.

## OUTPUT_PACKET_SCHEMA

```text
FIX evidence; local worktree paths; ACTUAL_EXECUTION_ROUTE
```

## WRITE_BOUNDARY

```text
ALLOWED (CONTROLLED_LIVE_UNCOMMITTED):
  local repository worktree writes within worker allowlist after valid RED
  (app/, tests/, openspec/changes/, results/FIX-*, …)
FORBIDDEN always:
  git commit / push / deploy / external production mutations
  GREEN self-confirm; shared identity with RED/GREEN
```

## TIMEOUT_SECONDS

```text
2400
```
