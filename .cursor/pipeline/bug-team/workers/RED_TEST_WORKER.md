# Worker: RED_TEST_WORKER

```text
WORKER_ID: RED_TEST_WORKER
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
TASK_SUBAGENT_TYPE: generalPurpose
MODEL_SELECTION_POLICY: inherit
MAPS_TO: /opsx-test (bug-regression)
```

## INPUT_PACKET_SCHEMA

```text
WORKER_IO + adjudication/fix_now or apply-ready packet
```

Common header: `packets/WORKER_IO.md`.

## OUTPUT_PACKET_SCHEMA

```text
RED evidence; TEST_IDs; TEST_CONTENT_SHA256; RED_CONFIRMED|PASS_ALREADY|INVALID_RED|...
```

## WRITE_BOUNDARY

```text
ALLOWED:
  tests/** (+fixtures); results/RED-*.md
FORBIDDEN:
  production writes; GREEN write; Owner GO forgery
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
ATTEMPT<=MAX_ATTEMPTS; never force artificial RED on valid PASS_ALREADY
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
