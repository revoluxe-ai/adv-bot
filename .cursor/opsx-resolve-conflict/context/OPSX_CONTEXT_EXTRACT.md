# OPSX_CONTEXT_EXTRACT — R34 / 0.34.0

Author: Cursor

## Purpose

Bounded extract so OPSX_CONTEXTUAL_REVIEW can proceed without a full repo dump.

## Authority lanes (command contract)

| Lane | Meaning |
|------|---------|
| A | OpenSpec/product change |
| B | Durable bug episode |
| C | OPSX/process surface |
| D | Ordinary product history |

## Process surfaces (write HIGH)

Prefixes/exact paths are machine-defined in `process_surfaces.json`.
GO sets `allow_process_write=False` by default.

## Graph / registry note

`.cursor/pipeline/GRAPH.md` is **advisory navigation**, not semantic GO/NO_GO
authority for conflict resolution.

Static checks: `.cursor/static-check/registry.yaml` + contracts/synthesis.md.

## Decision lookup order

1. Exact paths from change context
2. `openspec/decisions/index.md`
3. At most three targeted lookups

## Forbidden nested OPSX

Runtime must not invoke nested `/opsx-*` commands. Review of process surfaces
after process-path resolution uses `/opsx-review-commands REGRESSION_REVIEW`
(out of band).

## R20 GO semantic

Terminal success: `READY_FOR_OWNER_CONTINUE`  
Not claimed: history-advancing `RESOLVED`, verify GO, archive ready.


## R24 fail-closed authority / sandbox

- Consumer-only declaration verifier; no self-producer in this package.
- Missing producer contract → `BLOCKER_AUTHORITY_PRODUCER_MISSING`.
- Packaged runner is `BEST_EFFORT` only → `BLOCKER_OS_SANDBOX_RUNNER_MISSING` for GO.
- `GO_CAPABILITY=false` until both blockers close under independent acceptance.
