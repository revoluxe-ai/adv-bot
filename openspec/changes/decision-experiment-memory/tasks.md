# Tasks: decision-experiment-memory

Planning + phased implementation. **No production deploy in this change until
explicit Owner GO per slice.**

SCENARIO_PLAN_RECEIPT: openspec/changes/decision-experiment-memory/scenario-coverage/plan.receipt.json

## 0. Planning gates (this PR)

- [x] 0.1 `owner-contract.md`, `design.md`, delta spec, proposed ADR, `tasks.md`
- [x] 0.2 `scenario-coverage/plan.md` + `plan.receipt.json`
- [x] 0.3 `poetry run check-openspec` + `git diff --check`

## 1. Slice A — pure domain (no PostgreSQL)

- [ ] 1.1 Types: `DecisionMemoryRecord`, `ExperimentRecordV1`, `ExperimentPlanV1`,
  refs (`ApplyEvidenceRef`, settings/package/attribution pointers)
- [ ] 1.2 Enums: `experiment_design`, `treatment_mode`, `execution_state`, `outcome`,
  `validity_status`, protocol deviation codes
- [ ] 1.3 Plan registration/freeze: `plan_revision`, `plan_digest`, `PLAN_REGISTERED` /
  `PLAN_AMENDED` semantics (pure functions)
- [ ] 1.4 Invariants: independent ids; 1:N storage; APPLY_CONFIRMED requires BOUND
  Apply ref; LIVE exposure rules; execution_state ⊥ outcome
- [ ] 1.5 Reader port protocols (no IO)
- [ ] 1.6 Unit tests: cardinality, two-axis state, plan freeze, Apply-unbound paths

## 2. Slice B — persistence

- [ ] 2.1 Event model + Alembic forward-only tables (after Slice A GO)
- [ ] 2.2 Projections + repository implementing reader port
- [ ] 2.3 Idempotency keys per design (integration tests)

## 3. Slice C — linkage ingest

- [ ] 3.1 ChangeSet / dry-run receipt adapters
- [ ] 3.2 Apply audit → `ApplyEvidenceRef` binding (when apply-authority exists)
- [ ] 3.3 Settings history snapshot refs on decision/experiment timeline

## 4. Slice D — evaluation

- [ ] 4.1 Deterministic evaluator + validity assessment
- [ ] 4.2 Outcome recording, late metrics, correction events

## 5. Slice E — AI Package read exposure

- [ ] 5.1 Datasets `recent_decisions`, `active_experiments`, `experiment_results`
- [ ] 5.2 Manifest schema version bump + contract tests (no MCP server)

## 6. ADR promotion (separate Owner GO)

- [ ] 6.1 Promote `decision-experiment-memory-ownership` to `openspec/decisions/` Accepted
