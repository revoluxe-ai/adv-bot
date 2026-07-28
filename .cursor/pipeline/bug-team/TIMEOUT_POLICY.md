# Timeout / heartbeat / process-tree policy (Candidate)

```text
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
```

## Per-worker required fields

```text
STARTED_AT
LAST_HEARTBEAT_AT
TIMEOUT_SECONDS
PROGRESS_MARKER
PROCESS_ID
ATTEMPT
MAX_ATTEMPTS
CHECKPOINT_PATH
```

## Default limits (Candidate)

| Role | TIMEOUT_SECONDS | MAX_ATTEMPTS |
|------|-----------------|--------------|
| MATERIALIZER | 600 | 2 |
| CLAIM_WORKER | 300 | 2 |
| CLASSIFIER | 900 | 2 |
| SPEC_UPDATE_WORKER | 1800 | 2 |
| RED_TEST_WORKER | 2400 | 2 |
| IMPLEMENTATION_EXECUTOR | 2400 | 2 |
| GREEN_VERIFIER | 1800 | 2 |
| TASK_COMPLETION_WORKER | 600 | 2 |
| BOUNDED_HUNTER | 1800 | 2 |
| FAN_IN_ASSEMBLER | 600 | 2 |
| CLOSURE_OPERATOR | 300 | 1 |

No infinite automatic retries. Exhaustion → `MAX_RETRY_EXHAUSTED` terminal.

## States

```text
PENDING
RUNNING
WAITING_OWNER
PASS
FAIL
BLOCKED
TIMEOUT
CANCELLED
```

## Timeout procedure

1. Save checkpoint.
2. Append TIMEOUT event to `ROUTE-TRACE.jsonl`.
3. Terminate process tree (cancel sibling/child Task workers for this case).
4. Do not start next wave.
5. Return resumable state.
6. Do not hide partial artifacts.

## Hang detection

Orchestrator polls `LAST_HEARTBEAT_AT`. If
`now - LAST_HEARTBEAT_AT > TIMEOUT_SECONDS` while STATUS=RUNNING → TIMEOUT.
