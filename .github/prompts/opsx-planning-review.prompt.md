---
description: READ_ONLY independent review of a finished OpenSpec planning package before apply
---

# /opsx-planning-review

Independent **READ_ONLY** verifier of a finished OpenSpec planning package
before `/opsx-apply`.

**Canonical contract:** `.cursor/pipeline/contracts/PLANNING_REVIEW.md`  
**Command:** `.cursor/commands/opsx-planning-review.md`

Never mutate artifacts. Always emit `FILES_CHANGED: none`.

## Input

```text
/opsx-planning-review change=<change-id>
```

If change is ambiguous, ask once — do not invent the id.

## Behavior

1. Read planning artifacts under `openspec/changes/<change>/` (owner-contract,
   proposal, decisions, design, specs, tasks, scenario plan when required).
2. Run pillars P1–P8 from `PLANNING_REVIEW.md`. Treat READY /
   `NORMATIVE_MODALITY_PRESERVED` markers as evidence only — check bodies.
3. Identify `FIRST_BAD_ARTIFACT` (earliest upstream divergence), not only
   downstream symptoms.
4. Emit `PLANNING_REVIEW_RESULT` with terminal
   `PASS | REPAIR_REQUIRED | NEEDS_OWNER | BLOCKED`.
5. On `REPAIR_REQUIRED`, emit pasteable `/opsx-update` +
   `PLANNING_REVIEW_HANDOFF` (`MODE: REPAIR_PLANNING_PACKAGE`).
6. Do not invent product semantics; do not call update yourself; do not
   replace owner-contract-review, scenario coverage, PA, or verify.

## Footer

```text
MODE: READ_ONLY
FILES_CHANGED: none
```
