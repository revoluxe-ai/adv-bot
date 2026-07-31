# Worker I/O packet schema

```text
SCHEMA: opsx-bug-team/WORKER_IO
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
```

## Paths

```text
INPUT:  .tmp/opsx-bug-cases/<CASE_ID>/team/packets/<WEX>.in.md
OUTPUT: .tmp/opsx-bug-cases/<CASE_ID>/team/packets/<WEX>.out.md
```

## Common input header

```text
WORKER_ID:
WORKER_EXECUTION_ID:
PARENT_ORCHESTRATION_ID:
CASE_ID:
FINDING_ID:
ATTEMPT:
MAX_ATTEMPTS:
TIMEOUT_SECONDS:
ALLOWED_INPUT_ARTIFACTS:   # explicit list; no ambient peek
WRITE_BOUNDARY_SUMMARY:
HEARTBEAT_PATH:
OUTPUT_PACKET_PATH:
```

Workers may read **only** paths listed in `ALLOWED_INPUT_ARTIFACTS`.
Seeing another worker's raw output without being listed is a boundary violation.

## Common output header

```text
WORKER_ID:
WORKER_EXECUTION_ID:
PARENT_ORCHESTRATION_ID:
STATUS: PASS|FAIL|BLOCKED|TIMEOUT|WAITING_OWNER|CANCELLED
TERMINAL_STATUS:
STARTED_AT:
COMPLETED_AT:
LAST_HEARTBEAT_AT:
ARTIFACTS_WRITTEN: []
ERROR:
```

Malformed / missing required fields → orchestrator rejects packet
(`MALFORMED_OUTPUT_PACKET`) and does not advance the wave.
