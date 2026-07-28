# Worker: CLOSURE_OPERATOR

```text
WORKER_ID: CLOSURE_OPERATOR
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
TASK_SUBAGENT_TYPE: generalPurpose
MODEL_SELECTION_POLICY: auto
MAPS_TO: Owner-facing closure
```

## INPUT_PACKET_SCHEMA

```text
WORKER_IO + FANIN + OWNER_FINAL_CLOSURE_DECISION
```

Common header: `packets/WORKER_IO.md`.

## OUTPUT_PACKET_SCHEMA

```text
closure packet; case terminal recommendation
```

## WRITE_BOUNDARY

```text
ALLOWED:
  process closure artifacts only after Owner gate
FORBIDDEN:
  auto-close without Owner; act as FAN_IN_ASSEMBLER
```

## TIMEOUT_SECONDS

```text
300
```

## HEARTBEAT_POLICY

```text
update HEARTBEAT_PATH every <=30s
Required fields: STARTED_AT, LAST_HEARTBEAT_AT, PROGRESS_MARKER,
PROCESS_ID_OR_TASK_ID, ATTEMPT, CHECKPOINT_PATH, OUTPUT_ARTIFACT_PATH
```

## RETRY_POLICY

```text
MAX_ATTEMPTS: 1
MAX_ATTEMPTS=1
```

## DEPENDENCIES

```text
['FAN_IN_ASSEMBLER']
```

Next wave forbidden until this worker output passes schema + status +
authority validation.

## TERMINAL_STATES

```text
PASS|FAIL|BLOCKED|TIMEOUT|WAITING_OWNER|CANCELLED
```

## Dispatch

Must be launched via Cursor Task tool per
`dispatch/TASK_DISPATCH.md`. Must not be role-simulated by orchestrator.
