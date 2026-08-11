---
name: openspec-planning-review
description: "READ_ONLY independent review of a finished OpenSpec planning package before apply. Defers to PLANNING_REVIEW.md. Never writes."
---

# openspec-planning-review

Independent **READ_ONLY** verifier of a finished OpenSpec planning package
before `/opsx-apply`.

**Canonical contract (SoT):** `.cursor/pipeline/contracts/PLANNING_REVIEW.md`  
**Command mirror:** `.cursor/commands/opsx-planning-review.md`

Follow the contract for pillars P1–P8, finding schema, status model,
first-bad-artifact algorithm, and `PLANNING_REVIEW_HANDOFF`.

## Invocation

```text
/opsx-planning-review change=<change-id>
```

## Hard rules

* Never mutate files. Always `FILES_CHANGED: none`.
* Do not trust `DESIGN_STATUS: READY` / `TASKS_STATUS: READY` /
  `NORMATIVE_MODALITY_PRESERVED: yes` without body checks.
* Do not invent Owner semantics; do not auto-repair; do not call
  `/opsx-update` yourself.
* Soft gate before apply (v1). Not OCR, scenario coverage, PA, or verify.

## Output

Emit `PLANNING_REVIEW_RESULT` per contract. On `REPAIR_REQUIRED`, emit
pasteable `/opsx-update` + `PLANNING_REVIEW_HANDOFF`.
