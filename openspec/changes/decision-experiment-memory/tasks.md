## 1. Planning gate

- [x] 1.1 Initial planning package.
- [x] 1.2 Methodology addendum repair.
- [x] 1.2b Final architecture locks.
- [x] 1.3 Owner contract review — architecture accepted.
- [x] 1.4 Scenario coverage plan + receipt (`scenario-coverage/`).
- [x] 1.5 Spec repair: INVALID/INCONCLUSIVE mapping, `experiment_design`, abort projection.
- [ ] 1.6 `/opsx-planning-review change=decision-experiment-memory` PASS.
- [x] 1.7 ADL promoted to `openspec/decisions/decision-experiment-memory-ownership/`.
- [ ] 1.4 ADL promotion deferred until Owner accepts planning + post-review.

## 2. Slice A — domain vocabulary only (no PG, no Apply runtime)

**`SLICE_A_BLOCKED_BY_APPLY = NO`** — `ApplyEvidenceRef` types + invariants only.

- [x] 2.1 Domain types: `DecisionMemoryRecord`, `ExperimentRecordV1`, `ExperimentPlan`,
  `treatment_mode`, `ApplyEvidenceRef`, WindowModel, MetricSpecRef, ExposureModel,
  FactualResult, Interpretation, PostHocAnalysisRecord, ValiditySnapshot,
  EvaluationProvenance, InterventionSignature.
- [x] 2.2 Event taxonomy + projection rules (execution_state, outcome, plan freeze);
  cardinality 0..N compatible, V1 writer may enforce 0..1.
- [x] 2.3 `DecisionMemoryReader` + repository protocols; **test-only in-memory fake**
  (not production store).
- [x] 2.4 Unit tests: invariants (EVALUATED+INCONCLUSIVE, freeze gate, exposure gate,
  validity blocks SUCCEEDED/FAILED, observational causal level).
- [ ] 2.5 **Vocabulary freeze sign-off** before Slice B schema (pending post-repair certification).

## 3. Slice B — PostgreSQL persistence

- [ ] 3.1 Forward-only event tables + projections (after A freeze).
- [ ] 3.2 Idempotency indexes on receipt and evaluation digests.

## 4. Slice C — assignment / apply / exposure ingest

- [ ] 4.1 `EXPOSURE_CONFIRMED` from apply receipt + settings history.
- [ ] 4.2 ChangeSet metadata linkage.

## 5. Slice D — evaluation + validity + factual results

- [ ] 5.1 Deterministic evaluator (fixed horizon V1).
- [ ] 5.2 Optional `attribution_fact_set_ref` when contract deployed.
- [ ] 5.3 Confounder event ingest hooks.

## 6. Slice E — post-hoc + interpretation append

- [ ] 6.1 PostHocAnalysisRecord distinct from preregistered outcomes.

## 7. Slice F — AI Package `decision_memory_v1`

- [ ] 7.1 `recent_decisions`, `active_experiments`, `recent_experiment_results`,
  `experiment_memory_index`.

## 8. Verification (implementation phase)

- [ ] 8.1 `openspec validate --change decision-experiment-memory --strict`
- [ ] 8.2 Adjacent unit/integration per slice.
