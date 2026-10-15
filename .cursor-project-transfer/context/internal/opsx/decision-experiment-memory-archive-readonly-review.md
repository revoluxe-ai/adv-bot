---
cursor:
  subagentId: "bc-20525ca1-cf1f-5945-8312-36feb8b59a0e"
---

# decision-experiment-memory — post-archive READ_ONLY review

**Date:** 2026-10-09  
**Archive:** `openspec/changes/archive/2026-10-09-decision-experiment-memory/`  
**Mode:** READ_ONLY — `FILES_CHANGED: none`

## Checks requested

### 1) Main spec does not claim PG / evaluator / AI package delivered

**PASS.** `openspec/specs/decision-experiment-memory/spec.md`:

- Purpose limits delivery to Slice A foundation in `app/modules/decision_experiment_memory/`.
- Explicit out-of-scope: persistence, ingest, evaluator, AI export → `openspec/evolution/decision-experiment-memory-future-boundaries.md`.
- Requirement "Foundation scope" SHALL NOT provide PostgreSQL, ingest, evaluator runtime, or AI Package export.
- Evaluator: "Runtime evaluator enforcement is a future change."

No normative language asserts B–F slices are on `stage`.

### 2) `DryRunReceiptRef` vs `ApplyEvidenceRef` in app module

**PASS — aligned with spec.**

| Spec | Implementation (`domain/refs.py`) |
|------|-----------------------------------|
| `DryRunReceiptRef`: `dry_run_receipt_id` + optional binding digests | `dry_run_receipt_id`, `preview_digest`, `semantic_digest` |
| `ApplyEvidenceRef`: `apply_evidence_id`, optional digest, `authority_kind` | `apply_evidence_id`, `evidence_digest`, `authority_kind="APPLY_AUTHORITY"` |
| Distinct types, not polymorphic substitutes | Separate `@dataclass` types; docstring forbids interchange |

Usage: `DecisionMemoryRecord` / `EvaluationProvenance` use separate fields (`dry_run_receipt_ref` vs `apply_evidence_ref`). `projections.py` gates `APPLY_CONFIRMED` on `ApplyEvidenceRef`. Unit test `test_dry_run_receipt_ref_not_apply_evidence_ref` asserts `type(dry) is not type(apply)`.

No PG tables / alembic for this module; `InMemoryDecisionMemoryRepository` documented test-only.

### 3) Archive hygiene

| Item | Status |
|------|--------|
| Active `openspec/changes/decision-experiment-memory/` | Absent |
| Archive folder + `ARCHIVE_CLOSE_RECEIPT.md` | Present |
| Main spec vs archive delta body | Same requirements; main adds Purpose + `## Requirements` wrapper |
| ADL promoted | `openspec/decisions/decision-experiment-memory-ownership/decision.md` (Accepted) |
| Evolution boundaries | `openspec/evolution/decision-experiment-memory-future-boundaries.md` |

## Findings

| ID | Severity | Summary |
|----|----------|---------|
| F-001 | LOW | `scenario-coverage/certify.receipt.json` `evidence` path still `openspec/changes/decision-experiment-memory/FOUNDATION_CERTIFICATION.md` (file lives under archive path). |
| F-002 | LOW | `scenario-coverage/plan.receipt.json` PLAN_PATH/RECEIPT_PATH use pre-archive active-change paths. |
| F-003 | LOW | Promoted ADL `Related` links still cite `openspec/changes/decision-experiment-memory/...` ("delta until archive"). |

## Verdict

```
SEVERITY_COUNTS: CRITICAL=0 HIGH=0 MEDIUM=0 LOW=3
ARCHIVE_OK: YES
```

Core archive invariants (active change removed, main spec foundation-only, ref types match code) hold. Low findings are stale path strings in durable receipts/ADR cross-links only.
