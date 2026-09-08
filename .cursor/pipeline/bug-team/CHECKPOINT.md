# Checkpoint and resume (Candidate)

```text
SCHEMA: opsx-bug-team/CHECKPOINT
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
RUNTIME_PATH:
  .opsx/runs/bug-cases/<CASE_ID>/team/CHECKPOINT.md
```

## Required fields

```text
CASE_ID
FINDING_ID
CURRENT_ROUTE_STATE
COMPLETED_HOPS          # ordered list of ROLE_ID
ACTIVE_HOP              # ROLE_ID | null
EXPECTED_NEXT_COMMAND
OWNER_GATE_STATUS:
  NONE
  | WAITING_PRODUCTION_GO
  | PRODUCTION_GO_RECEIVED
  | WAITING_CLOSURE
  | CLOSURE_RECEIVED
  | BYPASS_REJECTED
ARTIFACT_PATHS
HASHES
ATTEMPTS                # map ROLE_ID → attempt count
LAST_HEARTBEAT_AT
CHECKPOINT_SCHEMA_VERSION: 1
UPDATED_AT
STALE: false | true
```

## Hop record (embedded)

```text
ROLE_ID
STARTED_AT
LAST_HEARTBEAT_AT
TIMEOUT_SECONDS
PROGRESS_MARKER
PROCESS_ID
ATTEMPT
MAX_ATTEMPTS
STATUS: PENDING|RUNNING|WAITING_OWNER|PASS|FAIL|BLOCKED|TIMEOUT|CANCELLED
CHECKPOINT_PATH
```

## Resume

```text
/opsx-bug-team case=<CASE_ID>
```

1. Load checkpoint.
2. If `STALE: true` → `BLOCKED_STALE_CHECKPOINT` (Owner decision).
3. Do **not** re-run hops in `COMPLETED_HOPS`.
4. Resume `ACTIVE_HOP` or `EXPECTED_NEXT_COMMAND`.
5. Never create a second case for the same resume.

## After TIMEOUT / BLOCKED

1. Persist checkpoint with partial artifacts visible.
2. Append TIMEOUT/BLOCKED route-trace event.
3. Terminate process tree (no next wave).
4. Return resumable state.
