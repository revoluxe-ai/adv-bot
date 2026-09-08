# Bug-team worker registry (Candidate)

```text
REGISTRY_ID: opsx-bug-team-workers
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: ACTIVE
OWNER_ACTIVATION: ISSUED
PIPELINE_GENERATION: ACTIVE_V1_WITH_INVARIANT_FANOUT_V10
BUG_FAMILY_FANOUT_ENABLED: true
BUG_FAMILY_FANOUT_STATUS: ACTIVE
ORCHESTRATOR_MODEL: registry_driven_cursor_task_pipeline
WORKER_MODEL: cursor_task_enum_worker
MODEL_SELECTION_POLICY: inherit
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
   - **`model: inherit`** (explicit — see `.cursor/pipeline/shared/MODEL_DISPATCH.md`);
   - unique `WORKER_EXECUTION_ID`;
   - input packet path under
     `.opsx/runs/bug-cases/<CASE_ID>/team/packets/`;
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
| FAMILY_LEARNING_WORKER | generalPurpose | mandatory LEARNING_DECISION (+ conditional packet) | `family/LEARNING_DECISION.json` or `results/LEARNING_DECISION.json`; optional `family/LEARNING_PACKET.json` |
| CLOSURE_OPERATOR | generalPurpose | Owner-facing closure packet | process artifacts; requires validated LEARNING_DECISION |
| INVARIANT_CAPTURE_WORKER | generalPurpose | post-root-GREEN invariant capture | `family/INVARIANT.md` + proof |
| RELATION_CLASSIFIER | generalPurpose | hunt candidate relation classify | findings + `family/` |
| INTEGRATION_OPERATOR | generalPurpose | branch patch integration | `family/INTEGRATION.json` |
| FAMILY_FAN_IN_ASSEMBLER | generalPurpose | family fan-in assemble | `results/FAMILY-FANIN.json\|.md` |

## Invariant-family fanout roles (ACTIVE)

```text
ACTIVATION_STATUS: ACTIVE
BUG_FAMILY_FANOUT_ENABLED: true
BUG_FAMILY_FANOUT_STATUS: ACTIVE
PIPELINE_GENERATION: ACTIVE_V1_WITH_INVARIANT_FANOUT_V10
SAME_INVARIANT_HUNT_FINDINGS: AUTOMATIC_FANOUT
MANUAL_SIBLING_RELAUNCH_REQUIRED: NO
EXECUTION_IDENTITY_GATE: ACTIVE
POLICY: .cursor/pipeline/bug-team/policy/BUG_FAMILY_FANOUT_POLICY.json
```

These roles run on the ACTIVE_V1 path after root GREEN when
`BUG_FAMILY_FANOUT_ENABLED=true`. Family workers remain gated by V10
execution-identity validation before orchestration advance.

## Anti-universal-worker rule

Forbidden: one worker that classifies **and** fixes **and** tests **and**
closes. Each ROLE_ID above is a separate hop with its own packet and
write boundary.

## Packet I/O convention

```text
INPUT:  .opsx/runs/bug-cases/<CASE_ID>/team/packets/<HOP_ID>.in.md
OUTPUT: .opsx/runs/bug-cases/<CASE_ID>/team/packets/<HOP_ID>.out.md
STATE:  .opsx/runs/bug-cases/<CASE_ID>/team/CHECKPOINT.md
TRACE:  .opsx/runs/bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
```

See `packets/WORKER_IO.md`.
