# Bug-episode shared schemas

```text
SCHEMA_ROOT: .cursor/pipeline/contracts/bug-episode/
POLICY_SOT: .cursor/pipeline/ORCHESTRATION_MVP.md
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
VALIDATION_STATUS: INDEPENDENT_TEST_PASS
RUNTIME_ENFORCEMENT: ACTIVE
LIVE_COMMAND_BEHAVIOR_CHANGED: YES
GO_ACTIVATE: ISSUED
```

## Role

This directory holds **field schemas** for product/logic bug episodes.

Normative policy (RED-before-GO, hunt bounds, lesson gate, fan-in checks)
lives in `ORCHESTRATION_MVP.md`. Commands **reference** these schemas; they
must not invent a second schema root.

## Files

| File | Purpose |
|------|---------|
| `RED_EVIDENCE.md` | RED evidence packet fields + statuses |
| `GREEN_EVIDENCE.md` | GREEN evidence packet fields + anti-weaken |
| `BRANCH_REGISTRY.md` | Schema definition for episode branch rows |
| `FANIN.md` | FANIN.md assemble input/output contract |
| `LESSON_GATE.md` | Class-level lesson gate preconditions |
| `TERMINAL_STATUS_MAP.md` | Episode terminal ↔ durable LEDGER status |
| `ROUTE_TRACE.md` | Append-only `ROUTE-TRACE.jsonl` event schema |
| `ROUTE_TRANSITION.md` | Machine hop packet consumed by `/opsx-supervisor` BUG_MISSION |
| `SUPERVISOR_POLICY.md` | Sequential mission execution policy (not route semantics) |
| `TASK_DELTA.md` | Post-`/opsx-update` task-delta → apply vs fix-bug |
| `CLOSE_POLICY.md` | Finding/case/class close; handback; solo walk; Owner-block explore |

## Classify-first routing (policy in ORCHESTRATION_MVP)

```text
BUG SIGNAL → materialize → claim → /opsx-classify-bug → Route A|B|C|D
```

Runtime current snapshot: `LEDGER.md` → `## ROUTE_STATE`.
Append-only history: `results/ROUTE-TRACE.jsonl`.

## BRANCH_REGISTRY shape (single runtime instance)

```text
SCHEMA DEFINITION:
  .cursor/pipeline/contracts/bug-episode/BRANCH_REGISTRY.md

RUNTIME INSTANCE (only):
  .tmp/opsx-bug-cases/<ROOT_CASE_ID>/LEDGER.md
    section "## BRANCH_REGISTRY"
```

Do **not** create a sibling `BRANCH_REGISTRY.md` file inside the case map.

## Fan-in write boundary

```text
CASE_MAP_WRITE_ALLOWED:
  .tmp/opsx-bug-cases/<ROOT_CASE_ID>/results/FANIN.md
ALL_OTHER_WRITES: DENIED
Mechanism: /opsx-materialize-bug-queue mode=fanin_assemble
NEW_SLASH: /opsx-fan-in-* FORBIDDEN
```

## Tokens that must stay distinct

```text
LEARNING_READY  ≠  FANIN_READY
claim STATUS    ≠  EPISODE_TERMINAL   (parallel fields)
/opsx-update    ≠  OWNER_PRODUCTION_GO
TASK_DELTA CHANGED  ≠  automatic /opsx-apply production permission
```
