---
description: "Candidate: registry-driven Cursor Task team for full bug lifecycle (free-form intake → classify → routes → RED/GO/GREEN → fan-in). NOT_ACTIVE until Owner activation."
argument-hint: "[free-form bug description] | signal=\"...\" | case=<CASE_ID>"
---

# /opsx-bug-team

```text
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
OWNER_ACTIVATION: NOT_ISSUED
SUBAGENT_EXECUTION_REQUIRED: YES
SINGLE_CHAT_ROLE_SIMULATION_ALLOWED: NO
SUBAGENT_RUNTIME_MODEL: CURSOR_TASK_WORKERS
MODEL_SELECTION_POLICY: auto
```

Передайте описание бага в свободной форме.
Команда сама материализует сигнал, проверит дубликаты,
создаст case и выберет безопасный маршрут.

**Activation blocker:** пока `RUNTIME_STATUS: NOT_ACTIVE` — команда
документирует Candidate-контракт и может запускать **controlled harness**
только. Не исполнять на реальном продуктовом баге и не выставлять
`ACTIVE` / `READY_FOR_PRODUCTION`.

## User input

```text
$ARGUMENTS
```

### Invocation modes

| Mode | Form |
|------|------|
| FREE_FORM_INLINE | `/opsx-bug-team <свободное описание>` |
| FREE_FORM_MULTILINE | `/opsx-bug-team` + multiline body |
| CURRENT_CONTEXT | `/opsx-bug-team` with empty args → current user message/context |
| EXPLICIT_SIGNAL | `/opsx-bug-team signal="..."` (optional) |
| CASE_RESUME | `/opsx-bug-team case=<CASE_ID>` |

```text
case=<CASE_ID> + new bug text  → BLOCKED_AMBIGUOUS_INVOCATION
empty args + no extractable signal → BLOCKED_INTAKE_REQUIRED
```

Do **not** require the user to supply CASE_ID / FINDING_ID /
BUG_CLASSIFICATION / structured evidence packets up front.

## Authority paths

```text
ORCHESTRATOR_ENTRYPOINT: .cursor/commands/opsx-bug-team.md
WORKER_REGISTRY_PATH:    .cursor/pipeline/bug-team/REGISTRY.md
TASK_DISPATCH_PATH:      .cursor/pipeline/bug-team/dispatch/TASK_DISPATCH.md
POLICY_SOT_LIVE:         .cursor/pipeline/ORCHESTRATION_MVP.md
CANDIDATE_PACKAGE:       .cursor/pipeline/bug-team/
```

## Orchestrator boundary (host chat ONLY)

Host Cursor chat may:

1. parse invocation / raw intake envelope;
2. read registry + durable checkpoint;
3. build allowed execution plan;
4. **launch Cursor Task subagents** (mandatory);
5. pass immutable input packets;
6. accept output packets;
7. validate packet schema + write boundary;
8. update orchestration state / DISPATCH.jsonl / CHECKPOINT;
9. stop on Owner gates;
10. start next wave only after prior gate PASS.

Host chat must **NOT**:

- classify instead of CLASSIFIER;
- author RED instead of RED_TEST_WORKER;
- change production instead of IMPLEMENTATION_EXECUTOR;
- confirm GREEN instead of GREEN_VERIFIER;
- perform independent review;
- assemble FANIN instead of FAN_IN_ASSEMBLER;
- role-play all workers inside one long prompt.

## Task dispatch (mandatory)

For **every** worker hop call the Cursor **Task** tool using the shape in
`.cursor/pipeline/bug-team/dispatch/TASK_DISPATCH.md`.

Rules:

- `subagent_type` from registry (`generalPurpose` unless specialized);
- **omit** `model` (auto / inherit only);
- unique `WORKER_EXECUTION_ID` per hop;
- append `.tmp/opsx-bug-cases/<CASE_ID>/team/DISPATCH.jsonl`;
- never invent missing worker output.

## Waves

```text
WAVE_1: MATERIALIZER → DUPLICATE_CHECK / CLAIM_WORKER
WAVE_2: CLASSIFIER
WAVE_3A Route A: RED → Owner production gate → EXECUTOR → GREEN
WAVE_3B Route B: SPEC_UPDATE → TASK_DELTA → RED → Owner GO → EXECUTOR → GREEN
WAVE_3C Route C: close recommendation (no implementation)
WAVE_3D Route D: durable ROUTE_TARGET_PROCESS_ID handoff
WAVE_4: TASK_COMPLETION → BOUNDED_HUNTER → FAN_IN → Owner closure → CLOSURE_OPERATOR
```

Next wave forbidden until prior worker output passes schema, status, and
authority validation.

## Owner gates

```text
RED_CONFIRMED → STOP → OWNER_PRODUCTION_GO_DECISION
FAN_IN_READY_FOR_OWNER_CLOSURE → STOP → OWNER_FINAL_CLOSURE_DECISION
```

## Classification (CLASSIFIER worker only)

Exactly one of:

```text
IMPLEMENTATION_BUG | SPEC_BUG | SPEC_GAP | FALSE_POSITIVE
| OUT_OF_SCOPE | INSUFFICIENT_EVIDENCE
```

## Route fields (never collapse)

```text
CHOSEN_ROUTE
EXPECTED_NEXT_COMMAND / ACTUAL_NEXT_COMMAND / NEXT_COMMAND_RECONCILIATION
EXPECTED_EXECUTION_ROUTE / ACTUAL_EXECUTION_ROUTE / ROUTE_RECONCILIATION
```

`/opsx-update` is never an execution route.

## Fan-in write boundary

`FAN_IN_ASSEMBLER` may write only:

```text
.tmp/opsx-bug-cases/<CASE_ID>/results/FANIN.md
```

## Timeout

Per-subagent timeout/heartbeat (see `TIMEOUT_POLICY.md`). On TIMEOUT:
checkpoint, terminate process tree, no dependent wave, no forged output.

## Commit / product boundary

```text
COMMIT_ALLOWED: NO   # this command never commits
app/** forbidden without Owner production GO via EXECUTOR worker
```

## Controlled tests

```bash
python .cursor/pipeline/bug-team/harness/run_controlled_tests.py
```

Builder runs ≠ Independent Tester PASS.

## When NOT_ACTIVE

If invoked while `RUNTIME_STATUS: NOT_ACTIVE`:

1. Refuse live product bug execution.
2. Report Candidate status + pasteable next:
   `Independent Candidate Team Review`
3. Optionally point to harness path for controlled verification only.
