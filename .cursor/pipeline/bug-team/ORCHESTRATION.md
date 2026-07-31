# Bug-team orchestration (Candidate)

```text
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
OWNER_ACTIVATION: NOT_ISSUED
POLICY_ALIGNMENT: .cursor/pipeline/ORCHESTRATION_MVP.md
```

## Waves (Candidate build)

| Wave | Scope | Status |
|------|-------|--------|
| WAVE_1 | contracts, schemas, registry | IMPLEMENTED_NOT_VALIDATED / NOT_ACTIVE |
| WAVE_2 | orchestration + routing + free-form intake | IMPLEMENTED_NOT_VALIDATED / NOT_ACTIVE |
| WAVE_3 | timeout, heartbeat, checkpoint, resume | IMPLEMENTED_NOT_VALIDATED / NOT_ACTIVE |
| WAVE_4 | controlled-test harness + command wiring | IMPLEMENTED_NOT_VALIDATED / NOT_ACTIVE |

Runtime enforcement must remain `NOT_ACTIVE` through WAVE_4.

## Subagent execution (hard)

```text
SUBAGENT_EXECUTION_REQUIRED: YES
SINGLE_CHAT_ROLE_SIMULATION_ALLOWED: NO
SUBAGENT_RUNTIME_MODEL: CURSOR_TASK_WORKERS
TASK_DISPATCH_PATH: .cursor/pipeline/bug-team/dispatch/TASK_DISPATCH.md
```

Each lifecycle hop below is a **separate Cursor Task** worker execution.
The host orchestrator must not perform worker duties itself.

## Lifecycle waves

```text
CONTROL_MODEL (default after activation):
  USER_REVIEWS_UNCOMMITTED_WORKTREE
DEFAULT_EXECUTION_MODE:
  CONTROLLED_LIVE_UNCOMMITTED

WAVE_1:
  MATERIALIZER (Task)
  → DUPLICATE_CHECK / CLAIM_WORKER (Task)

WAVE_2:
  CLASSIFIER (Task)

WAVE_3A — Route A:
  RED_TEST_WORKER (Task)
  → validate local execution authority (no Owner GO stop)
  → IMPLEMENTATION_EXECUTOR (Task)   # local uncommitted worktree writes
  → GREEN_VERIFIER (Task)

WAVE_3B — Route B:
  SPEC_UPDATE_WORKER (Task)
  → TASK_DELTA routing
  → RED_TEST_WORKER (Task)
  → validate local execution authority
  → IMPLEMENTATION_EXECUTOR (Task)
  → GREEN_VERIFIER (Task)

WAVE_3C — Route C:
  close recommendation without implementation (no RED/fix)

WAVE_3D — Route D:
  durable ROUTE_TARGET_PROCESS_ID handoff (no fake closure)

WAVE_4:
  TASK_COMPLETION_WORKER (Task)
  → BOUNDED_HUNTER (Task)
  → FAN_IN_ASSEMBLER (Task)   # writes ONLY results/FANIN.md
  → FAMILY_LEARNING_WORKER (Task)  # LEARNING_DECISION.json (+ conditional packet)
  → auto CLOSURE_OPERATOR when READY_FOR_CLOSURE + learning COMPLETE
  → HUMAN_SUMMARY.md + terminal CLOSED + AWAITING_USER_REVIEW
```

Legacy `EXECUTION_MODE=OWNER_GATED` still enforces Owner production/closure GO.

## Lifecycle (linear view)

```text
BUG SIGNAL (free-form | context | signal= | case= resume)
→ MATERIALIZER
→ CLAIM_WORKER (when claimable)
→ CLASSIFIER
→ Route A | B | C | D | INSUFFICIENT_EVIDENCE
→ (Route A/B) RED → local authority → IMPLEMENTATION_EXECUTOR
→ GREEN_VERIFIER
→ TASK_COMPLETION_WORKER
→ BOUNDED_HUNTER
→ FAN_IN_ASSEMBLER
→ FAMILY_LEARNING_WORKER
→ CLOSURE_OPERATOR (auto) + HUMAN_SUMMARY
→ USER reviews uncommitted worktree (no auto-commit)
```

## Canonical routes

### Route A

```text
IMPLEMENTATION_BUG
→ /opsx-fix-bug WITHOUT GO
→ RED
→ Owner production GO
→ production fix
→ independent GREEN
CHOSEN_ROUTE: ROUTE_A
EXPECTED_NEXT_COMMAND: /opsx-fix-bug
EXPECTED_EXECUTION_ROUTE: /opsx-fix-bug
```

### Route B

```text
SPEC_BUG | SPEC_GAP
→ /opsx-update
→ TASK_DELTA
CHOSEN_ROUTE: ROUTE_B
EXPECTED_NEXT_COMMAND: /opsx-update
EXPECTED_EXECUTION_ROUTE: PENDING_UNTIL_TASK_DELTA
```

```text
TASK_DELTA=CHANGED
→ EXPECTED_EXECUTION_ROUTE: /opsx-apply
→ EXPECTED_NEXT_COMMAND: /opsx-apply
→ RED → Owner GO → implementation → GREEN

TASK_DELTA=UNCHANGED
→ EXPECTED_EXECUTION_ROUTE: /opsx-fix-bug
→ EXPECTED_NEXT_COMMAND: /opsx-fix-bug
→ RED → Owner GO → fix → GREEN
```

`/opsx-update` is **never** `EXPECTED_EXECUTION_ROUTE` or
`ACTUAL_EXECUTION_ROUTE`.

### Route C

```text
FALSE_POSITIVE
→ CLOSED_NO_IMPLEMENTATION
No RED, no fix, no Owner production gate.
```

### Route D

```text
OUT_OF_SCOPE
→ ROUTE_TO_OTHER_PROCESS
ROUTE_TARGET_PROCESS_ID: required
ROUTE_TARGET_REASON: required
Missing target → BLOCKED_MISSING_ROUTE_TARGET
```

### Insufficient evidence

```text
INSUFFICIENT_EVIDENCE
→ BLOCKED_EVIDENCE_REQUIRED
Stop without choosing a production route.
```

## Route fields (never collapse)

```text
CHOSEN_ROUTE
EXPECTED_NEXT_COMMAND
ACTUAL_NEXT_COMMAND
NEXT_COMMAND_RECONCILIATION

EXPECTED_EXECUTION_ROUTE
ACTUAL_EXECUTION_ROUTE
ROUTE_RECONCILIATION
```

Mismatch → `BLOCKED_ROUTE_MISMATCH`; no production GO; no episode close.

## Owner / local authority gates

### Default: CONTROLLED_LIVE_UNCOMMITTED

```text
RED_CONFIRMED → validate local execution authority → IMPLEMENTATION_EXECUTOR
FANIN READY_FOR_CLOSURE + BLOCKING_FINDINGS=NONE
  → FAMILY_LEARNING_WORKER
  → auto CLOSURE_OPERATOR (requires validated LEARNING_DECISION)
```

Local worktree writes allowed after valid RED. No intermediate Owner GO / closure stop.
Commit/push/deploy remain forbidden (user reviews uncommitted tree).

### Legacy: OWNER_GATED

```text
RED_CONFIRMED → STOP → OWNER_PRODUCTION_GO_DECISION
FAN_IN_READY_FOR_OWNER_CLOSURE → STOP → OWNER_FINAL_CLOSURE_DECISION
```

Bypass attempts → rejected (`OWNER_GATE_BYPASS_REJECTED`).

Fan-In Assembler must not close the case (FAMILY_LEARNING_WORKER then CLOSURE_OPERATOR only).
Learning worker must not close the case (CLOSURE_OPERATOR only).
Closure must not skip LEARNING_DECISION.

## Claim authority

Forbidden:

```text
duplicate active root
two active claims for one finding
claim bypass
known case resumed as new case
```

Legacy resume: explicit `AUTHORITY_MODE: LEGACY_RESUME` — no fictitious
backdated claim.

## Free-form intake (WAVE_2)

Primary UX: raw user text. Materializer owns normalization.
See `packets/RAW_INTAKE.md`.
