# Worker: SPEC_UPDATE_WORKER

```text
WORKER_ID: SPEC_UPDATE_WORKER
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
TASK_SUBAGENT_TYPE: generalPurpose
MODEL_SELECTION_POLICY: inherit
MAPS_TO: /opsx-update
```

## INPUT_PACKET_SCHEMA

```text
WORKER_IO + classification ROUTE_B receipt
```

Common header: `packets/WORKER_IO.md`.

## OUTPUT_PACKET_SCHEMA

```text
TASK_DELTA CHANGED|UNCHANGED + evidence path + execution route fields
```

## WRITE_BOUNDARY

```text
ALLOWED:
  OpenSpec planning artifacts; TASK-DELTA-*.md; route state
FORBIDDEN:
  production GO; EXPECTED_EXECUTION_ROUTE=/opsx-update; code edits
```

## TIMEOUT_SECONDS

```text
1800
```

## HEARTBEAT_POLICY

```text
update HEARTBEAT_PATH every <=60s
Required fields: STARTED_AT, LAST_HEARTBEAT_AT, PROGRESS_MARKER,
PROCESS_ID_OR_TASK_ID, ATTEMPT, CHECKPOINT_PATH, OUTPUT_ARTIFACT_PATH
```

## RETRY_POLICY

```text
MAX_ATTEMPTS: 2
ATTEMPT<=MAX_ATTEMPTS
```

## DEPENDENCIES

```text
['CLASSIFIER']
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
