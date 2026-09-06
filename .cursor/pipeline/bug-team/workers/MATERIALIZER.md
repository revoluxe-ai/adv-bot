# Worker: MATERIALIZER

```text
WORKER_ID: MATERIALIZER
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
TASK_SUBAGENT_TYPE: generalPurpose
MODEL_SELECTION_POLICY: inherit
MAPS_TO: /opsx-materialize-bug-queue mode=intake|update
```

## INPUT_PACKET_SCHEMA

```text
packets/RAW_INTAKE.md + WORKER_IO input
```

Common header: `packets/WORKER_IO.md`.

## OUTPUT_PACKET_SCHEMA

```text
RAW_INTAKE normalized + case/finding ids + DUPLICATE_OUTCOME
```

## WRITE_BOUNDARY

```text
ALLOWED:
  .tmp/opsx-bug-cases/<CASE_ID>/intakes/**, findings/**, CASE.md, LEDGER (materialize), team packets out
FORBIDDEN:
  classify; propose fix; Owner GO; production
```

## TIMEOUT_SECONDS

```text
600
```

## HEARTBEAT_POLICY

```text
update HEARTBEAT_PATH every <=60s while RUNNING
Required fields: STARTED_AT, LAST_HEARTBEAT_AT, PROGRESS_MARKER,
PROCESS_ID_OR_TASK_ID, ATTEMPT, CHECKPOINT_PATH, OUTPUT_ARTIFACT_PATH
```

## RETRY_POLICY

```text
MAX_ATTEMPTS: 2
ATTEMPT<=MAX_ATTEMPTS; no infinite retry
```

## DEPENDENCIES

```text
[]
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
