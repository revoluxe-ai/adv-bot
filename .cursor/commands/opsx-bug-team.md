---
description: "Active registry-driven Cursor Task team for full bug lifecycle (free-form intake → classify → routes → RED/fix/GREEN → invariant-family fanout → fan-in). Owner-activated CONTROLLED_LIVE_UNCOMMITTED."
argument-hint: "[free-form bug description] | signal=\"...\" | case=<CASE_ID>"
---

# /opsx-bug-team

```text
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: ACTIVE
OWNER_ACTIVATION: ISSUED
ACTIVATION_MODE: CONTROLLED_LIVE_UNCOMMITTED
PIPELINE_GENERATION: ACTIVE_V1_WITH_INVARIANT_FANOUT_V10
BUG_FAMILY_FANOUT_ENABLED: true
BUG_FAMILY_FANOUT_STATUS: ACTIVE
DEFAULT_FULL_BUG_ENTRY: /opsx-bug-team
SAME_INVARIANT_HUNT_FINDINGS: AUTOMATIC_FANOUT
MANUAL_SIBLING_RELAUNCH_REQUIRED: NO
FINAL_CONTROL: OWNER_REVIEWS_UNCOMMITTED_GIT_DIFF
SUBAGENT_EXECUTION_REQUIRED: YES
SINGLE_CHAT_ROLE_SIMULATION_ALLOWED: NO
SUBAGENT_RUNTIME_MODEL: CURSOR_TASK_WORKERS
MODEL_SELECTION_POLICY: inherit
COMMIT_AUTHORITY: OWNER_ONLY
GIT_COMMIT: FORBIDDEN
GIT_PUSH: FORBIDDEN
DEPLOY: FORBIDDEN
```

Передайте описание бага в свободной форме.
Команда сама материализует сигнал, проверит дубликаты,
создаст case и выберет безопасный маршрут.

**Current status:** Owner-activated (`RUNTIME_STATUS: ACTIVE`) in
`CONTROLLED_LIVE_UNCOMMITTED`. Root-bug ACTIVE_V1 path remains the default
entry; invariant-family fanout V8–V10 is enabled after root GREEN.
Command-native v2 remains planned separately.

## Hard activation runtime gate (BF-007 — mandatory first step)

Before **any** materialization or Task dispatch, read:

```text
.cursor/pipeline/bug-team/ACTIVATION.json
```

via `runtime/activation.py` (`check_invocation_gate`).

```text
NORMAL / real-intake-shaped invocation + RUNTIME_STATUS != ACTIVE
→ STATUS: BLOCKED_CANDIDATE_NOT_ACTIVE
→ TASK_DISPATCH_COUNT: 0
→ do not call Task tool
→ do not create real .opsx/runs/bug-cases cases
```

Allowed exception only:

```text
EXECUTION_MODE: REVIEW_PROOF_ONLY
proof root under .tmp/opsx-bug-team-harness/
product writes forbidden
synthetic CASE_ID/FINDING_ID
no Owner GO
no activation mutation
```

Current activation receipt:

```text
.cursor/pipeline/bug-team/INVARIANT_FAMILY_FANOUT_ACTIVATION_RECEIPT.json
```

## Invariant-family fanout V8–V10 (ACTIVE)

```text
V8_IMPLEMENTATION: ACTIVE
V9_CORRECTIVE: APPLIED (invariant proof / fan-in JSON / learning / parallelism)
V10_CORRECTIVE: APPLIED (authoritative execution identity validation)
BUG_FAMILY_FANOUT_ENABLED: true
BUG_FAMILY_FANOUT_STATUS: ACTIVE
POLICY: .cursor/pipeline/bug-team/policy/BUG_FAMILY_FANOUT_POLICY.json
RUNTIME: runtime/family_policy.py + runtime/bug_family.py + runtime/family_fanout.py
         + runtime/invariant_proof.py + runtime/parallelism.py + runtime/execution_identity.py
CONTROLLED_TEST_MODE: CONTROLLED_TEST_FAMILY_FANOUT
V8_TESTS: harness/run_corrective_v8_tests.py
V9_TESTS: harness/run_corrective_v9_tests.py
V10_TESTS: harness/run_corrective_v10_tests.py
CURRENT_ACTIVE_RUNTIME: ACTIVE_V1_WITH_INVARIANT_FANOUT_V10
EXECUTION_IDENTITY_GATE: ACTIVE
```

After root GREEN, the pipeline captures a testable invariant, materializes
hunt candidates, classifies relation, fans out same-invariant branches with
isolated patches, integrates, runs family-wide GREEN, family fan-in, learning,
then family closure. Same-invariant hunt findings **MUST** fan out (or receive
a durable FALSE_POSITIVE / OUT_OF_SCOPE disposition) **before** episode
`FANIN_READY` / `READY_FOR_CLOSURE` — HARD_BLOCK_READY (see
`.cursor/pipeline/contracts/bug-episode/FANIN.md` and
`policy/BUG_FAMILY_FANOUT_POLICY.json` BLOCKING_RULES). Listing an
`OPEN_CANDIDATE` SAME_INVARIANT residual as non-blocking
(`BLOCKS_ROOT_CLOSURE=false` / `may_need_family_fanout` while READY) is
Forbidden. If auto fanout did not run, emit `FANIN_INCOMPLETE` and resume:
`case=<CASE_ID> mode=resume-family-fanout` (manual relaunch is recovery, not
an optional skip of the gate). Soft: also recommend
`/opsx-bug-debt-board case=<CASE_ID>` so residual OPEN_CANDIDATE debt is
visible outside the team chat.

Relation outcomes:

```text
SAME_INVARIANT_FINDING → branch fanout (blocks family closure until terminal;
                         also blocks episode FANIN_READY while OPEN_CANDIDATE)
NEW_ROOT_CAUSE         → linked case (does not block parent family closure)
FALSE_POSITIVE         → durable rejection
OUT_OF_SCOPE           → durable handoff
INCONCLUSIVE           → family OPEN_BLOCKED
```

V9: invariant↔root-GREEN proof validation; canonical `FAMILY-FANIN.json`;
complete learning packet; parallelism eligibility/dispatch/observation split;
policy-derived `BLOCKS_FAMILY_CLOSURE`; Cursor agent ID identity records.

V10: `validate_execution_identity` reconciles canonical
`team/executions/<WEX>.identity.json` against DISPATCH.jsonl, input/output
packets, checkpoint, attempt/generation, and real `CURSOR_AGENT_ID`. Terminal
orchestration advance requires `EXECUTION_IDENTITY_VALIDATION: PASS` /
`IDENTITY_STATUS: VALIDATED`. Identity JSON alone is not authority.

## Corrective V7 runtime modules (uncommitted worktree control)

```text
CONTROL_MODEL:  USER_REVIEWS_UNCOMMITTED_WORKTREE
CONTROL:        runtime/control_model.py
DEFAULT_MODE:   CONTROLLED_LIVE_UNCOMMITTED
OWNER_GATED:    preserved for EXECUTION_MODE=OWNER_GATED
V7_TESTS:       harness/run_corrective_v7_tests.py
```

## Corrective V6 runtime modules (ICT SR copy-replay)

```text
RETRY_AUTH:     runtime/retry_auth.py  (immutable receipt + append-only registry)
IDEMPOTENCY:    unchanged from V5
V6_TESTS:       harness/run_corrective_v6_tests.py
```

## Corrective V5 runtime modules (ICT rerun blockers)

```text
IDEMPOTENCY:    prepare fingerprint + exact input/deps/contract/boundary match
TOCTOU:         validate_dispatch_intent_before_task before Task dispatch
RETRY_AUTH:     durable one-time retry authorization bound to real previous WEX
V5_TESTS:       harness/run_corrective_v5_tests.py
```

## Corrective V4 runtime modules (ICT blockers)

```text
OWNER_HOST:     runtime/owner_decision_host.py  (RED raw+canonical at reserve)
LIVE_HOP:       runtime/live_task_hop.py        (sole success authority + ACTIVE lock)
ORCHESTRATOR:   finalize_after_task → BLOCKED_LEGACY_FINALIZE_DISABLED
PACKETS:        validate_packet LIVE_TRANSITION_AUTHORITY: NONE
AUTHORITY_INV:  runtime/LIVE_SUCCESS_AUTHORITY.md
V4_TESTS:       harness/run_corrective_v4_tests.py
```

## Corrective V3 runtime modules

```text
ACTIVATION:     .cursor/pipeline/bug-team/ACTIVATION.json
PACKETS:        runtime/packets.py          (validate_packet_for_transition)
FS_BOUNDARY:    runtime/fs_boundary.py      (snapshot diff, not self-report)
OWNER_HOST:     runtime/owner_decision_host.py  (host-only GO registration)
OWNER_GO:       runtime/owner_go.py         (create_* FORBIDDEN for workers)
LIVE_HOP:       runtime/live_task_hop.py    (authoritative prepare→Task→finalize)
WORKER_CONTRACTS: runtime/worker_contracts.py
ROUTE_TRACE:    runtime/route_trace.py      (append-only v2)
TIMEOUT:        runtime/timeout.py          (honest platform limits)
ORCHESTRATOR:   runtime/orchestrator.py     (delegates to live_task_hop; Task is host)
DISPATCH_SOT:   dispatch/TASK_DISPATCH.md
SIMULATED:      harness/task_dispatch.py    (LIVE_RUNTIME_AUTHORITY: NONE)
```

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
| CASE_RESUME | `/opsx-bug-team case=BUGCASE-…` (durable id only) |

```text
durable case=BUGCASE-… + new bug text  → BLOCKED_AMBIGUOUS_INVOCATION
placeholder case=<CASE_ID> / case=CASE_ID     → ignored (treat as absent;
  free-form / signal proceeds)  # CMD-IX-001
empty args + no extractable signal → BLOCKED_INTAKE_REQUIRED
```

**First-intake paste fence (CMD-IX-002):** free-form / `RAW_REPORT` first
intake MUST NOT include `case=` resume lines or `ALSO_OK` `/opsx-explore`
handbacks in the same message. Those belong only after a durable
`CASE_ID` exists (separate paste / CASE_RESUME).

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
9. apply control-model gates (local uncommitted authority or legacy Owner GO);
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
- **`model: inherit`** (explicit — see `.cursor/pipeline/shared/MODEL_DISPATCH.md`);
- unique `WORKER_EXECUTION_ID` per hop;
- append `.opsx/runs/bug-cases/<CASE_ID>/team/DISPATCH.jsonl` per
  `TASK_DISPATCH.md` **Append recipe** (prefer `live_task_hop`; ad-hoc
  Shell/Python MUST follow
  `.cursor/commands/opsx-execution-preflight.md` →
  **Shell payload I/O (anti-heredoc)** and
  **Windows Shell JSON / JSONL write safety** —
  no bash heredoc for multi-line JSON/Python; Write→path first; on heredoc
  failure switch Write→path once; `encoding="utf-8"` + `ensure_ascii=True`;
  no `ensure_ascii=False` stdin recipes; no unsafe console print of the line);
- never invent missing worker output.

## Waves

```text
WAVE_1: MATERIALIZER → DUPLICATE_CHECK / CLAIM_WORKER
WAVE_2: CLASSIFIER
WAVE_3A Route A: RED → local authority → EXECUTOR → GREEN
WAVE_3B Route B: SPEC_UPDATE → TASK_DELTA → RED → local authority → EXECUTOR → GREEN
WAVE_3C Route C: close recommendation (no implementation)
WAVE_3D Route D: durable ROUTE_TARGET_PROCESS_ID handoff
WAVE_4: TASK_COMPLETION → BOUNDED_HUNTER → FAN_IN → FAMILY_LEARNING_WORKER → auto CLOSURE_OPERATOR
         (+ HUMAN_SUMMARY.md; user reviews uncommitted worktree)
```

Legacy `OWNER_GATED`: intermediate Owner production GO + Owner closure GO still apply.

Next wave forbidden until prior worker output passes schema, status, and
authority validation.

## Owner gates

```text
CONTROL_MODEL:
  USER_REVIEWS_UNCOMMITTED_WORKTREE

DEFAULT after activation:
  RED_CONFIRMED → local authority → IMPLEMENTATION_EXECUTOR
  (no WAITING_OWNER / Owner production GO)

  FANIN READY_FOR_CLOSURE → FAMILY_LEARNING_WORKER → auto CLOSURE_OPERATOR
  (no WAITING_OWNER_FINAL_CLOSURE; learning decision mandatory;
   HARD_BLOCK_READY: open SAME_INVARIANT OPEN_CANDIDATE forbids READY /
   closure — resume-family-fanout first; INDEX must list residual debt;
   soft: `/opsx-bug-debt-board case=<CASE_ID>` to surface residual debt)

Legacy EXECUTION_MODE=OWNER_GATED:
  RED_CONFIRMED → STOP → OWNER_PRODUCTION_GO_DECISION
  FAN_IN_READY_FOR_OWNER_CLOSURE → STOP → OWNER_FINAL_CLOSURE_DECISION

Always forbidden:
  git commit / git push / deploy / external production mutations
```

### Owner-block UX (A/B/C / policy / INSUFFICIENT_EVIDENCE)

When the team **stops** for Owner adjudication (`OWNER_A_B_C_UNRESOLVED`,
policy choice, or equivalent), the host output MUST include — no silent
auto-continue into the next wave without these lines:

```text
OWNER_DECISION_REQUIRED: A | B | C | <exact choices>
OPTIONAL_IF_UNSURE:
/opsx-explore case=CASE_ID finding=FINDING_ID
THEN_RETURN (pasteable — never silent):
/opsx-bug-team case=CASE_ID mode=continue
```

Substitute durable `BUGCASE-…` / finding ids from INDEX/LEDGER — do **not**
emit angle-bracket `case=<CASE_ID>` templates (CMD-IX-001). Omit these
lines until ids are known. Never paste them into first-intake `RAW_REPORT`
(CMD-IX-002).

Authority: `.cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md`.
Explore clarifies; it does **not** replace A/B/C. After Owner answers in
explore (or here), resume only via the pasteable `THEN_RETURN` (or explicit
Owner `GO continue team` in this chat).

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
.opsx/runs/bug-cases/<CASE_ID>/results/FANIN.md
```

`FAMILY_LEARNING_WORKER` may write:

```text
family/LEARNING_DECISION.json   # or results/LEARNING_DECISION.json (episode-only)
family/LEARNING_PACKET.json     # only when FULL_PACKET_REQUIRED
results/LEARNING_REPORT.md
```

`CLOSURE_OPERATOR` may write:

```text
results/OWNER-CLOSURE-<FINDING_ID>.md
results/HUMAN_SUMMARY.md
CASE.md / LEDGER.md / findings / INDEX.md
ROUTE-TRACE.jsonl closure events
```

Final user control:

```text
WORKTREE_STATUS: UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
COMMIT_CREATED: NO
USER_ACTION_REQUIRED: REVIEW_DIFF_AND_DECIDE_COMMIT
```

Chat must end with section `ПРОСТОЕ ОБЪЯСНЕНИЕ` (plain language).

## Timeout

Per-subagent timeout/heartbeat (see `TIMEOUT_POLICY.md` and
`dispatch/TASK_DISPATCH.md`).

```text
CURSOR_TASK_CANCELLATION: PARTIAL_INTERRUPT_ON_RESUME
PROCESS_TREE_TERMINATION: BLOCKED_PLATFORM_TERMINATION_LIMITATION
SAFE_TIMEOUT_ENFORCEMENT: logical state isolation; dependent-wave stop;
  stale/late-output rejection; finite retry
```

On TIMEOUT: checkpoint ACTIVE isolation, no dependent wave, no forged output.

## Commit / product boundary

```text
COMMIT_ALLOWED: NO   # this command never commits
app/** forbidden without Owner production GO via EXECUTOR worker
```

## Controlled tests

```bash
python .cursor/pipeline/bug-team/harness/run_controlled_tests.py
python .cursor/pipeline/bug-team/harness/run_corrective_v10_tests.py
python .cursor/pipeline/bug-team/harness/run_corrective_v9_tests.py
python .cursor/pipeline/bug-team/harness/run_corrective_v8_tests.py
python .cursor/pipeline/bug-team/harness/run_corrective_v7_tests.py
python .cursor/pipeline/bug-team/harness/run_corrective_v6_tests.py
python .cursor/pipeline/bug-team/harness/run_corrective_v5_tests.py
python .cursor/pipeline/bug-team/harness/run_corrective_v4_tests.py
python .cursor/pipeline/bug-team/harness/run_corrective_v3_tests.py
python .cursor/pipeline/bug-team/harness/run_corrective_tests.py
```

Builder runs ≠ Independent Tester PASS.

## When NOT_ACTIVE (historical / fail-closed)

If `ACTIVATION.json` were reverted to `RUNTIME_STATUS: NOT_ACTIVE`:

1. Refuse live product bug execution.
2. Report Candidate status + pasteable next:
   `Independent Candidate Team Review`
3. Optionally point to harness path for controlled verification only.

Current workspace state is `RUNTIME_STATUS: ACTIVE` with
`BUG_FAMILY_FANOUT_ENABLED: true`.

