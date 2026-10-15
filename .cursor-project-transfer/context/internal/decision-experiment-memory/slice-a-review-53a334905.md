---
cursor:
  subagentId: "bc-aab57a5b-bf0a-5488-b571-a8cfb89cb3ac"
---

# Slice A code review — `cursor/decision-experiment-memory-slice-a-eb40` @ `53a334905`

**Scope:** DryRunReceiptRef vs ApplyEvidenceRef, PostHocAnalysisRecord, no ORM / apply-persistence coupling.  
**Baseline:** merged `origin/stage` @ `7a3fe886`.

## Verdict

| Severity | Count |
|----------|------:|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 2 |

**MERGE_READY:** YES

## Evidence run

- `poetry run pytest -m unit tests/unit/decision_experiment_memory/` → **49 passed**
- `poetry run pyright-strict app/modules/decision_experiment_memory` → **0 errors**

## Focus areas (pass)

### ApplyEvidenceRef vs DryRunReceiptRef

- Separate frozen datatypes in `domain/refs.py` with docstring stating non-interchangeability.
- `EvaluationProvenance` carries `apply_evidence_ref: ApplyEvidenceRef | None` and `dry_run_receipt_ref: DryRunReceiptRef | None` (payload-free).
- Unit test `test_dry_run_receipt_ref_not_apply_evidence_ref` asserts distinct types and co-presence on provenance.
- Apply execution gates use **only** `ApplyEvidenceRef`: `project_decision_status`, `validate_confirmed_exposure`, `link_decision_status` on in-memory fake; covered by `test_live_exposure_and_ports` / slice_a_domain tests.
- No receipt-body fields on ref types; `ExposureConfirmedPayload` stores ids/digests only.

### PostHocAnalysisRecord

- Dataclass in `domain/factual.py` with `PostHocAnalysisKind`, optional exploratory `MetricSpecRef`s, links to `interpretation_id`.
- Tests confirm exploratory metrics do not alter `plan_body_digest` (distinct from preregistered plan).
- Not on `DecisionMemoryReader` / fake store — aligned with Slice E task 6.1 (runtime deferred); acceptable for Slice A vocabulary-only deliverable.

### No ORM / apply persistence coupling

- New module is dataclasses + protocols + test fake only; **no** `sqlalchemy`, `app.utils.db`, or PG adapters under `app/modules/decision_experiment_memory/`.
- `testing/in_memory_repository.py` header states TEST-ONLY, Slice B+ for PostgreSQL.
- No imports from `wb_sky_control_plane.apply` persistence layers.

## Findings

### MEDIUM — decision-level dry-run shape vs frozen `DryRunReceiptRef`

`DecisionMemoryRecord` exposes `dry_run_receipt_id: str | None` while `apply_evidence_ref` is typed `ApplyEvidenceRef | None`. ADL validation linkage is documented as `dry_run_receipt_id` **+ digest**; `DryRunReceiptRef` includes `preview_digest` / `semantic_digest`. Provenance layer is correct; decision aggregate may force Slice B to encode a weaker shape or duplicate id-only columns unless normalized before merge to B.

**Suggestion (Slice B planning):** migrate decision linkage to `DryRunReceiptRef | None` or document explicit two-tier model in design.

### LOW — PostHocAnalysisRecord not on ports

Type + unit tests only; no `get_post_hoc_analysis` on reader. Expected for Slice A; track with task 6.1.

### LOW — `ExposureConfirmedPayload` flattens apply ref

Event payload uses scalar `apply_evidence_id` / `evidence_digest` instead of embedding `ApplyEvidenceRef`. Serialization convenience only; no dry-run confusion.

## Out of scope (not blocking Slice A merge)

- tasks.md §1.6 formal planning-review receipt open
- Slice B+ PG, Apply ingest, evaluator, AI Package
- Full scenario-coverage audit (S24 CONTRIBUTION vocabulary only)

## Branch / PR

- Repo: `adv-bot`
- Branch: `cursor/decision-experiment-memory-slice-a-eb40`
- Commit: `53a334905`
