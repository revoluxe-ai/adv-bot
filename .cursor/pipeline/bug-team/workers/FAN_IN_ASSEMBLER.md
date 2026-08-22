# Worker: FAN_IN_ASSEMBLER

```text
WORKER_ID: FAN_IN_ASSEMBLER
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
TASK_SUBAGENT_TYPE: generalPurpose
MODEL_SELECTION_POLICY: auto
MAPS_TO: materialize mode=fanin_assemble
```

## INPUT_PACKET_SCHEMA

```text
WORKER_IO + completed evidence packet paths only
```

Common header: `packets/WORKER_IO.md`.

## OUTPUT_PACKET_SCHEMA

```text
FANIN.md fields; STATUS FANIN_READY|FANIN_INCOMPLETE
HARD_BLOCK_READY: open SAME_INVARIANT candidates → FANIN_INCOMPLETE
  + BLOCKING_FINDINGS (never READY_FOR_CLOSURE / BLOCKS_ROOT_CLOSURE=false)
```

Authority: `.cursor/pipeline/contracts/bug-episode/FANIN.md` (HARD_BLOCK_READY).
Assembler MUST scan hunt residuals / `findings/HC-*` / FANIN input for
`RELATION_TO_ROOT_CANDIDATE=SAME_INVARIANT_FINDING` with open_candidate status.
If any remain undisposed → emit `FANIN_INCOMPLETE` and pasteable
`/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout`.

## WRITE_BOUNDARY

```text
ALLOWED:
  ONLY .tmp/opsx-bug-cases/<CASE_ID>/results/FANIN.md
FORBIDDEN:
  LEDGER; ROUTE-TRACE; CASE; findings; INDEX; production; tests; OpenSpec; .cursor; checkpoint
```

INDEX obligation for open SAME_INVARIANT residuals is owned by
`/opsx-materialize-bug-queue` / orchestrator INDEX refresh — not this worker.

ACTIVE_V1 root fan-in. When V8 family fanout is Owner-enabled, prefer
`FAMILY_FAN_IN_ASSEMBLER` / `results/FAMILY-FANIN.md` per
`policy/BUG_FAMILY_FANOUT_POLICY.json` (do not duplicate rules here).

## TIMEOUT_SECONDS

```text
600
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
['BOUNDED_HUNTER']
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
