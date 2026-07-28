# Bug-team worker registry (Candidate)

```text
REGISTRY_ID: opsx-bug-team-workers
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
ORCHESTRATOR_MODEL: registry_driven_cursor_task_pipeline
WORKER_MODEL: cursor_task_enum_worker
MODEL_SELECTION_POLICY: auto
```

## How workers are invoked

```text
SUBAGENT_EXECUTION_REQUIRED: YES
SINGLE_CHAT_ROLE_SIMULATION_ALLOWED: NO
TASK_DISPATCH_PATH: .cursor/pipeline/bug-team/dispatch/TASK_DISPATCH.md
WORKER_SPECS_DIR: .cursor/pipeline/bug-team/workers/
```

1. `/opsx-bug-team` (ORCHESTRATOR) reads this registry.
2. For each hop, orchestrator launches **one** Cursor **Task** tool worker
   with:
   - `subagent_type` mapped from `TASK_SUBAGENT_TYPE` below (or
     `generalPurpose` when no specialized enum exists);
   - model inherit only (**omit** `model`);
   - unique `WORKER_EXECUTION_ID`;
   - input packet path under
     `.tmp/opsx-bug-cases/<CASE_ID>/team/packets/`;
   - required output packet path;
   - `TIMEOUT_SECONDS` / heartbeat contract from `TIMEOUT_POLICY.md`;
   - durable line in `team/DISPATCH.jsonl`.
3. Workers do **not** self-register. Registration is this file only.
4. Do **not** use `.cursor/agents/*` (repo does not use that runtime).
5. Host chat role-simulation of workers is an **activation blocker**.

## Registry entries

| ROLE_ID | TASK_SUBAGENT_TYPE | Maps to live command / mechanism | Writes |
|---------|--------------------|----------------------------------|--------|
| ORCHESTRATOR | (slash command host) | `/opsx-bug-team` | checkpoint, route-trace, team state |
| MATERIALIZER | generalPurpose | `/opsx-materialize-bug-queue mode=intake\|update` | case map intake/finding |
| CLAIM_WORKER | generalPurpose | `/opsx-claim-next-bug` | claim token / finding STATUS |
| CLASSIFIER | generalPurpose | `/opsx-classify-bug` | ROUTE_STATE + route-trace |
| SPEC_UPDATE_WORKER | generalPurpose | `/opsx-update` | OpenSpec planning + TASK_DELTA |
| RED_TEST_WORKER | generalPurpose | `/opsx-test` (bug-regression) | tests + RED evidence |
| IMPLEMENTATION_EXECUTOR | generalPurpose | `/opsx-fix-bug GO` or `/opsx-apply` | production after Owner GO |
| GREEN_VERIFIER | generalPurpose | `/opsx-test verify` | GREEN evidence only |
| TASK_COMPLETION_WORKER | generalPurpose | evidence-mapped OpenSpec `[x]` | tasks.md checkboxes only with evidence |
| BOUNDED_HUNTER | generalPurpose | `/opsx-bug-hunt` / project hunt bounds | candidate findings only |
| FAN_IN_ASSEMBLER | generalPurpose | materialize `mode=fanin_assemble` | **only** `results/FANIN.md` |
| CLOSURE_OPERATOR | generalPurpose | Owner-facing closure packet | process artifacts; no auto-close |

## Anti-universal-worker rule

Forbidden: one worker that classifies **and** fixes **and** tests **and**
closes. Each ROLE_ID above is a separate hop with its own packet and
write boundary.

## Packet I/O convention

```text
INPUT:  .tmp/opsx-bug-cases/<CASE_ID>/team/packets/<HOP_ID>.in.md
OUTPUT: .tmp/opsx-bug-cases/<CASE_ID>/team/packets/<HOP_ID>.out.md
STATE:  .tmp/opsx-bug-cases/<CASE_ID>/team/CHECKPOINT.md
TRACE:  .tmp/opsx-bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
```

See `packets/WORKER_IO.md`.
