# Worker: GREEN_VERIFIER

```text
WORKER_ID: GREEN_VERIFIER
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
TASK_SUBAGENT_TYPE: generalPurpose
MODEL_SELECTION_POLICY: inherit
MAPS_TO: /opsx-test verify
```

## INPUT_PACKET_SCHEMA

```text
WORKER_IO + RED packet + FIX evidence (listed only)
```

Common header: `packets/WORKER_IO.md`.

## OUTPUT_PACKET_SCHEMA

```text
GREEN evidence; frozen hash match; route reconciliation check
```

## WRITE_BOUNDARY

```text
ALLOWED:
  results/GREEN-*.md only
FORBIDDEN:
  production/test edits; reuse Executor WEX/context
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
['IMPLEMENTATION_EXECUTOR']
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
