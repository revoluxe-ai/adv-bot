# Timeout / heartbeat / process-tree policy (Candidate)

```text
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
```

## Platform discovery (honest — BF-006)

```text
CURSOR_TASK_CANCELLATION: PARTIAL_INTERRUPT_ON_RESUME
PROCESS_TREE_TERMINATION: BLOCKED_PLATFORM_TERMINATION_LIMITATION
SAFE_TIMEOUT_STOP: IMPLEMENTED
LATE_OUTPUT_REJECTION: IMPLEMENTED
```

Evidence: Cursor Task tool supports `interrupt=true` when resuming a
**running** async agent. No general process-tree kill API is proven for
the OPSX orchestrator. Python harness subprocess kill is **not** Cursor
Task cancellation.

Runtime module: `runtime/timeout.py`
Status dump: `runtime/TIMEOUT_PLATFORM_STATUS.json`

## Per-worker required fields

```text
STARTED_AT
LAST_HEARTBEAT_AT
TIMEOUT_SECONDS
PROGRESS_MARKER
PROCESS_ID_OR_TASK_ID
ATTEMPT
MAX_ATTEMPTS
CHECKPOINT_PATH
PACKET_GENERATION
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
| FAMILY_LEARNING_WORKER | 900 | 2 |
| CLOSURE_OPERATOR | 300 | 1 |

Exhaustion → `BLOCKED_MAX_RETRY_EXHAUSTED`. No infinite retries.

## Safe timeout stop

1. Detect heartbeat timeout.
2. Mark worker TIMEOUT; persist TIMEOUT event.
3. Do not dispatch dependent workers.
4. Persist resumable checkpoint.
5. Retain partial artifacts.
6. Reject late output via generation/attempt validation.
7. Resume requires a new execution attempt.

Do **not** claim `PROCESS_TREE_TERMINATION_IMPLEMENTED: YES`.
