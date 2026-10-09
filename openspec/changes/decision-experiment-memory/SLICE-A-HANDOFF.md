# Slice A implementation handoff (separate change)

**Owner GO:** planning accepted; **Slice A not authorized in planning PR.**

## Authorized scope

- Domain enums / value objects under `app/modules/decision_experiment_memory/`
- `DecisionMemoryRecord`, `ExperimentRecordV1`, `ExperimentPlan` + freeze/revision invariants
- `execution_state`, `outcome`, validity vocabulary (`demem_outcome_v1`)
- `MetricSpecRef`, window model refs, `EvaluationProvenance` refs
- `ApplyEvidenceRef` types only (no ingest)
- `intervention_signature` pure functions
- `DecisionMemoryReader` / repository **protocols**
- **Test-only** `InMemoryDecisionMemoryRepository` fake
- Unit tests + scenario evidence for Slice A rows in `scenario-coverage/plan.md`

## Forbidden

PostgreSQL, Alembic, production persistence, Apply ingest, evaluator runtime,
attribution implementation, AI Package, MCP, REST, deploy.

## Authority

- ADL: `openspec/decisions/decision-experiment-memory-ownership/decision.md`
- Spec delta: `openspec/changes/decision-experiment-memory/specs/decision-experiment-memory/spec.md`
- Scenario plan: `scenario-coverage/plan.md` (S01–S11, S14–S19, S23, S25, S26 + projection rules)

## Suggested first command (new chat)

Implement OpenSpec change `decision-experiment-memory` **Slice A only** per
`tasks.md` §2 and `SLICE-A-HANDOFF.md`. Run targeted unit tests; then
`/opsx-spec-scenario-coverage mode=audit change=decision-experiment-memory`.
