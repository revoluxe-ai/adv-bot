# Controlled test matrix T1–T26 (+ extras)

```text
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
HARNESS: .cursor/pipeline/bug-team/harness/run_controlled_tests.py
INDEPENDENT_TESTER_PASS: NOT_ISSUED
```

## Run (Builder only)

```bash
python .cursor/pipeline/bug-team/harness/run_controlled_tests.py
```

## Matrix

| ID | Assertion |
|----|-----------|
| T1 | Route A normal flow to RED stop / Owner production gate |
| T2 | Route B TASK_DELTA=CHANGED to RED stop |
| T3 | Route B TASK_DELTA=UNCHANGED to RED stop |
| T4 | Route C early close without implementation |
| T5 | Route D durable handoff target |
| T6 | INSUFFICIENT_EVIDENCE blocked stop |
| T7 | production Owner-gate bypass rejected |
| T8 | closure Owner-gate bypass rejected |
| T9 | duplicate claim / claim bypass rejected |
| T10 | worker timeout + process-tree termination + checkpoint |
| T11 | resume after TIMEOUT/BLOCKED without repeating completed hops |
| T12 | FAN_IN_ASSEMBLER write-boundary violation rejected |
| T13 | one-line free-form Russian intake → materialized case/finding |
| T14 | multiline unstructured intake → verbatim + normalized |
| T15 | no-arg command uses current message context |
| T16 | incomplete intake → INSUFFICIENT_EVIDENCE safe stop |
| T17 | raw intake matching active root → duplicate rejected/linked |
| T18 | case= + new free-form → BLOCKED_AMBIGUOUS_INVOCATION |
| T19 | dispatches real MATERIALIZER Task worker; orchestrator does not materialize |
| T20 | Route A distinct RED, Executor, GREEN worker executions |
| T21 | Route B distinct Spec Update, RED, Executor, GREEN |
| T22 | GREEN cannot reuse Executor execution identity |
| T23 | timed-out worker prevents dependent wave dispatch |
| T24 | malformed output packet rejected |
| T25 | production worker write-boundary violation terminates execution |
| T26 | Fan-In receives completed evidence only; writes only FANIN.md |

## Extras

| ID | Assertion |
|----|-----------|
| X_PARTIAL_W2 | partial WAVE_2 stop |
| X_PREMATURE_ACTIVE | premature ACTIVE forbidden |
| X_PASS_ALREADY | PASS_ALREADY without forced RED |
| X_HASH_MISMATCH | frozen test hash mismatch |
| X_ROUTE_MISMATCH | route reconciliation mismatch |
| X_MAX_RETRY | max retry exhaustion bounded |

## Subagent proof note

Harness backends stand in for Cursor Task **process boundary** while still:

1. building real Task tool argument objects (`to_cursor_task_arguments`);
2. allocating distinct `WORKER_EXECUTION_ID` per hop;
3. appending `DISPATCH.jsonl` with `CURSOR_TASK_TOOL: Task`;
4. forbidding orchestrator self-materialization.

Live `/opsx-bug-team` (when activated) must call the Cursor **Task** tool
per `dispatch/TASK_DISPATCH.md` — not role-play workers in the host chat.
