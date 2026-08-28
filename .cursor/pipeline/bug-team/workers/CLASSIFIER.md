# Worker: CLASSIFIER

```text
WORKER_ID: CLASSIFIER
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
TASK_SUBAGENT_TYPE: generalPurpose
MODEL_SELECTION_POLICY: inherit
MAPS_TO: /opsx-classify-bug
```

## INPUT_PACKET_SCHEMA

```text
WORKER_IO + finding/intake packets only
```

Common header: `packets/WORKER_IO.md`.

## OUTPUT_PACKET_SCHEMA

```text
exactly one CLASSIFICATION + CHOSEN_ROUTE + route fields
```

## WRITE_BOUNDARY

```text
ALLOWED:
  ROUTE-TRACE append; LEDGER ## ROUTE_STATE only
FORBIDDEN:
  OpenSpec edits; production; tests; fix plan execution
```

## TIMEOUT_SECONDS

```text
900
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
['MATERIALIZER']
```

Next wave forbidden until this worker output passes schema + status +
authority validation.

## TERMINAL_STATES

```text
PASS|FAIL|BLOCKED|TIMEOUT|CANCELLED
```

## Dispatch

Must be launched via Cursor Task tool per
`dispatch/TASK_DISPATCH.md`. Must not be role-simulated by orchestrator.
