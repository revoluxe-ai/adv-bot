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
WORKER_IO + RED_CONFIRMED + OWNER_PRODUCTION_GO receipt
```

Common header: `packets/WORKER_IO.md`.

## OUTPUT_PACKET_SCHEMA

```text
FIX evidence; production paths; ACTUAL_EXECUTION_ROUTE
```

## WRITE_BOUNDARY

```text
ALLOWED:
  production only after Owner GO; no test mutate by default
FORBIDDEN:
  GO bypass; GREEN self-confirm; shared identity with RED/GREEN
```

## TIMEOUT_SECONDS

```text
2400
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
['RED_TEST_WORKER']
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
