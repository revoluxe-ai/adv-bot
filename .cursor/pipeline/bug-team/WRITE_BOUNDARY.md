# Write-boundary policy (Candidate)

```text
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
```

## FAN_IN_ASSEMBLER (hard)

Sole allowed write:

```text
.opsx/runs/bug-cases/<CASE_ID>/results/FANIN.md
```

Forbidden for FAN_IN_ASSEMBLER:

```text
LEDGER.md
ROUTE-TRACE.jsonl
CASE.md
findings/**
INDEX.md
production / app/**
tests/**
OpenSpec/**
.cursor/**
team/CHECKPOINT.md   # orchestrator-owned
```

Any other write attempt → `FANIN_WRITE_BOUNDARY_VIOLATION` rejected.

Mechanism alignment: live
`/opsx-materialize-bug-queue mode=fanin_assemble`.

## ORCHESTRATOR

Allowed:

```text
.opsx/runs/bug-cases/<CASE_ID>/team/**          # packets, checkpoint, DISPATCH
.opsx/runs/bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl  # append only
.opsx/runs/bug-cases/<CASE_ID>/LEDGER.md  ## ROUTE_STATE / team summary only
```

Forbidden:

```text
performing MATERIALIZER/CLASSIFIER/RED/EXECUTOR/GREEN/FANIN duties
production / app/**
business tests
OpenSpec product changes
premature ACTIVE / READY_FOR_PRODUCTION status tokens
forging a failed worker's output packet
```

## GREEN_VERIFIER

Allowed: GREEN evidence under case map only.
Forbidden: production / tests / OpenSpec.

## IMPLEMENTATION_EXECUTOR

```text
CONTROLLED_LIVE_UNCOMMITTED (default after activation):
  local worktree writes after LOCAL_IMPLEMENTATION_AUTHORIZED (valid RED)
  Owner production GO NOT required

OWNER_GATED (legacy):
  production / worktree writes only after Owner production GO + RED gate
```

Forbidden always: git commit / push / deploy / external mutations / GREEN self-confirm.

## CLOSURE_OPERATOR

Allowed:

```text
results/OWNER-CLOSURE-<FINDING_ID>.md
results/HUMAN_SUMMARY.md
CASE.md / LEDGER.md / findings/** / INDEX.md
ROUTE-TRACE.jsonl closure events
```

Forbidden: rewriting FANIN.md; claiming COMMITTED / DEPLOYED / PUSHED.

## Candidate package write boundary (Builder)

Preferred:

```text
.cursor/commands/opsx-bug-team.md
.cursor/pipeline/bug-team/**
.cursor/pipeline/GRAPH.md
.cursor/pipeline/META.md
```

Forbidden without Owner expansion:

```text
app/**
tests/unit/auto_updater_v3/**
openspec/changes/card-ab-hold-mode/**
```
