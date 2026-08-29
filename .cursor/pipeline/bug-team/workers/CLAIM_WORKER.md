# Worker: CLAIM_WORKER

```text
WORKER_ID: CLAIM_WORKER
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
TASK_SUBAGENT_TYPE: generalPurpose
MODEL_SELECTION_POLICY: inherit
MAPS_TO: /opsx-claim-next-bug
```

## INPUT_PACKET_SCHEMA

```text
WORKER_IO + finding queue snapshot
```

Common header: `packets/WORKER_IO.md`.

## OUTPUT_PACKET_SCHEMA

```text
CLAIM_TOKEN + FINDING_ID + STATUS=claimed | blocker
```

## WRITE_BOUNDARY

```text
ALLOWED:
  findings/**; CASE.md (ROOT_FINDING_ID / stage when minting root);
  intakes/** (link SOURCE_INTAKE only); LEDGER claim row;
  team/packets/; team/heartbeats/; results/PROOF-
FORBIDDEN:
  claim bypass; invent CLAIM_TOKEN; dual active claim;
  production; classify rewrite; OpenSpec
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
