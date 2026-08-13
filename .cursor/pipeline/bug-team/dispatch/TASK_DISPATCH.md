# Task dispatch protocol (Candidate)

```text
SCHEMA: opsx-bug-team/TASK_DISPATCH
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
SINGLE_CHAT_ROLE_SIMULATION_ALLOWED: NO
SUBAGENT_RUNTIME_MODEL: CURSOR_TASK_WORKERS
```

## Paths

```text
ORCHESTRATOR_ENTRYPOINT: .cursor/commands/opsx-bug-team.md
WORKER_REGISTRY_PATH:    .cursor/pipeline/bug-team/REGISTRY.md
TASK_DISPATCH_PATH:      .cursor/pipeline/bug-team/dispatch/TASK_DISPATCH.md
DISPATCH_IMPL_PATH:      .cursor/pipeline/bug-team/harness/task_dispatch.py
WORKER_SPECS_DIR:        .cursor/pipeline/bug-team/workers/
```

## Hard rule

The host Cursor chat (`ORCHESTRATOR`) **must** launch each worker via the
Cursor **Task** tool (registry-driven Task workers).

Forbidden:

```text
orchestrator self-classifies as CLASSIFIER
orchestrator authors RED as RED_TEST_WORKER
orchestrator edits production as IMPLEMENTATION_EXECUTOR
orchestrator confirms GREEN as GREEN_VERIFIER
orchestrator assembles FANIN as FAN_IN_ASSEMBLER
orchestrator writes LEARNING_DECISION as FAMILY_LEARNING_WORKER
orchestrator closes case as CLOSURE_OPERATOR without learning
one long prompt that role-plays all workers in-sequence
```

## Cursor Task call shape (mandatory)

For every worker hop the orchestrator issues **exactly one** Task invocation:

```text
Tool: Task
arguments:
  description: "opsx-bug-team/<WORKER_ID>"   # short UI title
  subagent_type: <TASK_SUBAGENT_TYPE from REGISTRY>
  # model: OMIT — inherit / auto only
  run_in_background: false | true   # true only for long workers with heartbeat
  prompt: |
    WORKER_ID: <WORKER_ID>
    WORKER_EXECUTION_ID: <WEX/...>
    PARENT_ORCHESTRATION_ID: <ORCH/...>
    CASE_ID: <CASE_ID>
    FINDING_ID: <FINDING_ID or null>
    INPUT_PACKET_PATH: <absolute or repo-relative .in.md>
    OUTPUT_PACKET_PATH: <absolute or repo-relative .out.md>
    WRITE_BOUNDARY_PATH: .cursor/pipeline/bug-team/WRITE_BOUNDARY.md
    WORKER_SPEC_PATH: .cursor/pipeline/bug-team/workers/<WORKER_ID>.md
    TIMEOUT_SECONDS: <n>
    ATTEMPT: <n>
    MAX_ATTEMPTS: <n>
    CHECKPOINT_PATH: .tmp/opsx-bug-cases/<CASE_ID>/team/CHECKPOINT.md
    HEARTBEAT_PATH: .tmp/opsx-bug-cases/<CASE_ID>/team/heartbeats/<WEX>.json
    MODEL_SELECTION_POLICY: auto
    FORBIDDEN: do not perform other workers' duties
    REQUIRED: write OUTPUT_PACKET only within WRITE_BOUNDARY;
              update HEARTBEAT_PATH periodically;
              exit with terminal STATUS in output packet
```

`model` must never be set. Prefer registry `TASK_SUBAGENT_TYPE`.

## Supervisor host top-level (cross-ref)

When `/opsx-supervisor` launches **this whole command** as one top-level
Task (`/opsx-bug-team` primary), host clocks and Owner-visible rules come
from `/opsx-supervisor` §12.0–§12.4 (not from the child-role table alone):

```text
TOP_LEVEL_TIMEOUT_SECONDS default: 3600
TOP_LEVEL_NO_PROGRESS_TIMEOUT_SECONDS default: 900
OWNER_VISIBLE_DISPATCH: required before/at launch
run_in_background: preferred true when platform heartbeat works
platform abort/interrupt → PAUSED EXECUTION_OUTCOME_UNKNOWN (no ADVANCE)
```

Child worker `TIMEOUT_SECONDS` rows in `TIMEOUT_POLICY.md` still apply
**inside** the team; they do not authorize unbounded host wait.

## Dispatch record (durable)

After each Task launch / completion, orchestrator appends one line to:

```text
.tmp/opsx-bug-cases/<CASE_ID>/team/DISPATCH.jsonl
```

Required fields:

```text
SCHEMA_VERSION: 1
WORKER_EXECUTION_ID
PARENT_ORCHESTRATION_ID
WORKER_ID
TASK_SUBAGENT_TYPE
CURSOR_TASK_TOOL: Task
STARTED_AT
LAST_HEARTBEAT_AT
TIMEOUT_SECONDS
ATTEMPT
MAX_ATTEMPTS
PROCESS_ID_OR_TASK_ID      # Task tool agent id when returned
CHECKPOINT_PATH
INPUT_PACKET_PATH
OUTPUT_ARTIFACT_PATH
STATUS: PENDING|RUNNING|WAITING_OWNER|PASS|FAIL|BLOCKED|TIMEOUT|CANCELLED
TERMINAL_STATUS
SCHEMA_VALID: true|false
WRITE_BOUNDARY_OK: true|false
```

### Append recipe (mandatory)

Prefer authoritative `runtime/live_task_hop.py` (or other sealed dispatch
helpers) over ad-hoc stdin Python.

If the orchestrator must append via Shell/Python, follow
`.cursor/commands/opsx-execution-preflight.md` →
**Windows Shell JSON / JSONL write safety**:

```text
encoding="utf-8" on every open/write
ensure_ascii=True for agent-authored recipes
no print of the JSONL line to a cp1251 console
ASCII "->" (not "→") in machine-written string fields
```

Do not use `json.dumps(..., ensure_ascii=False)` in agent Shell/stdin
recipes for `DISPATCH.jsonl` — that pattern fails on Windows `cp1251`
when payload text contains `→` or other non-ASCII.

## Orchestrator-only duties

```text
parse invocation / raw intake envelope (not normalize — MATERIALIZER does)
read registry + checkpoint
build execution plan
write immutable .in.md packets
call Task tool
validate .out.md schema + write boundary
update CHECKPOINT + ROUTE-TRACE
stop on Owner gates
start next wave only after prior gate PASS
```

## Independence matrix (must not share execution identity)

```text
RED_TEST_WORKER           ≠ IMPLEMENTATION_EXECUTOR
IMPLEMENTATION_EXECUTOR   ≠ GREEN_VERIFIER
SPEC_UPDATE_WORKER         ≠ any reviewer role
BOUNDED_HUNTER            ≠ IMPLEMENTATION_EXECUTOR
FAN_IN_ASSEMBLER          ≠ FAMILY_LEARNING_WORKER
FAMILY_LEARNING_WORKER    ≠ CLOSURE_OPERATOR
FAN_IN_ASSEMBLER          ≠ CLOSURE_OPERATOR

Live WAVE_4 terminal edges:
  FAN_IN_ASSEMBLER → FAMILY_LEARNING_WORKER → CLOSURE_OPERATOR
```

Each inequality ⇒ distinct `WORKER_EXECUTION_ID` and distinct Cursor Task run.

## Timeout isolation

Timeout is **per Task subagent**, not one global command timer only.

```text
CURSOR_TASK_CANCELLATION: PARTIAL_INTERRUPT_ON_RESUME
PROCESS_TREE_TERMINATION: BLOCKED_PLATFORM_TERMINATION_LIMITATION
SAFE_TIMEOUT_ENFORCEMENT:
  logical state isolation
  dependent-wave stop
  stale/late-output rejection
  finite retry
```

On TIMEOUT:

1. Mark that `WORKER_EXECUTION_ID` as TIMEOUT in DISPATCH.jsonl / checkpoint ACTIVE_STATUS.
2. Do **not** claim unconditional OS process-tree kill — platform limitation applies;
   use `PARTIAL_INTERRUPT_ON_RESUME` when resuming/cancelling via Cursor Task.
3. Keep partial output if any; reject late/stale finalize for that WEX.
4. Do not dispatch dependent workers.
5. Persist resumable CHECKPOINT with new ACTIVE WEX on retry.
6. Orchestrator must **not** fabricate the missing output packet.

Live hop authority: `.cursor/pipeline/bug-team/runtime/live_task_hop.py`.

## Fan-out

Allowed only for independent read-only probes (separate WEX each).
Forbidden: parallel competing production executors.

## Activation blocker

Independent Review PASS / runtime activation **forbidden** if:

- workers are only roles inside one prompt;
- no factual Task dispatch path / DISPATCH.jsonl;
- RED and GREEN share one execution identity;
- timeout is only command-global;
- no worker-level checkpoints;
- orchestrator silently replaces a failed worker.
