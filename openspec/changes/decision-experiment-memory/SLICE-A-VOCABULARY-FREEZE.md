# Slice A vocabulary freeze sign-off

CHANGE: decision-experiment-memory  
STATUS: FROZEN_FOR_SLICE_B_PLANNING  
DATE: 2026-10-07

Frozen vocabulary (domain + ports + test fake only):

- Identity: `decision_id` / `experiment_id` independence; 1→N experiments
- `ExperimentPlanBody` **B** incl. `switchback_schedule` (reserved struct, no engine)
- `plan_digest = sha256(canonical_json(B))` via `plan_serialization`
- `ApplyEvidenceRef`: `apply_evidence_id`, `evidence_digest`, `authority_kind="APPLY_AUTHORITY"`
- LIVE exposure gate; `EXPOSURE_CONFIRMED` event refs (no receipt body)
- `MetricSpecRef` + analysis window refs; validity/outcome `demem_outcome_v1`
- `CONFOUNDER_DETECTED` vocabulary; reader port surface on `DecisionMemoryReader`
- Event append vs projection upsert ports

Not frozen here: PG schema, Apply ingest, evaluator, attribution runtime, AI Package.
