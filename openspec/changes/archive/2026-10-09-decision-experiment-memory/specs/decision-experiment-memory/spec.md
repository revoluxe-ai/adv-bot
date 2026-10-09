# decision-experiment-memory

## ADDED Requirements

### Requirement: Foundation scope (Slice A module)

The delivered implementation SHALL be limited to transport-independent domain
vocabulary, projection rules, reader/repository protocols, and a **test-only**
`InMemoryDecisionMemoryRepository` under `app/modules/decision_experiment_memory/`.
It SHALL NOT provide PostgreSQL persistence, Apply/exposure ingest, deterministic
evaluator runtime, or AI Package export.

#### Scenario: No production memory store in foundation

- **GIVEN** the foundation module on `stage`
- **WHEN** production runtime wiring is inspected
- **THEN** no decision-memory PostgreSQL tables or production singleton fake MUST exist

### Requirement: Decision memory does not duplicate authoritative payloads

The system MUST store semantics and immutable references (IDs, digests, tokens).
It MUST NOT copy full settings snapshots, ChangeSet bodies, dry-run receipt bodies,
or Apply evidence payloads as SoT.

#### Scenario: Decision view exposes refs not authoritative payloads

- **GIVEN** a decision with settings and ChangeSet linkage refs
- **WHEN** a reader loads the decision view
- **THEN** the view MUST expose tokens and digests only

### Requirement: Dry-run vs apply evidence references are distinct

Validation evidence MUST use `DryRunReceiptRef` (opaque `dry_run_receipt_id` plus
optional binding digests from Apply Authority). Execution evidence MUST use
`ApplyEvidenceRef` (`apply_evidence_id`, optional digest, `authority_kind`).
The types MUST NOT be polymorphic substitutes.

#### Scenario: Dry-run ref is not apply evidence ref

- **GIVEN** `EvaluationProvenance` or `DecisionMemoryRecord` carrying both refs
- **WHEN** types are inspected
- **THEN** `dry_run_receipt_ref` and `apply_evidence_ref` MUST use distinct types

### Requirement: Independent decision and experiment identities

`DecisionMemoryRecord` MUST be keyed by `decision_id`. `ExperimentRecordV1` MUST
be keyed by `experiment_id` and MUST reference exactly one `decision_id`.
`experiment_id` MUST NOT be required to equal `decision_id`.

#### Scenario: Distinct ids for one decision-experiment pair

- **GIVEN** `decision_id=D1` and `experiment_id=E1`
- **WHEN** the experiment is modeled
- **THEN** `E1` MAY differ from `D1`
- **AND** the experiment MUST reference `decision_id=D1`

### Requirement: Decision to experiment cardinality

The domain contract MUST allow one decision to have zero or many experiments (0..N).

#### Scenario: Domain allows multiple experiments per decision

- **GIVEN** one `decision_id`
- **WHEN** multiple `experiment_id` values reference it
- **THEN** the domain model MUST remain valid without 1:1 identity coupling

### Requirement: Treatment mode orthogonal to experiment design

Each experiment MUST declare `treatment_mode` (`LIVE` | `SHADOW`) separately from
`experiment_design`. Observational design MUST NOT gain causal strength via treatment mode.

#### Scenario: Shadow observational study

- **GIVEN** `experiment_design=BEFORE_AFTER_OBSERVATIONAL` and `treatment_mode=SHADOW`
- **WHEN** causal level is derived
- **THEN** `causal_evidence_level` MUST reflect observational design

### Requirement: Apply and exposure projection invariants

Without `ApplyEvidenceRef`, `APPLY_CONFIRMED` MUST NOT be assigned. Without
authoritative effective-state evidence, confirmed LIVE `OBSERVING` MUST NOT be assigned
and `treatment_effective_from` MUST NOT be guessed.

#### Scenario: No apply evidence no apply confirmed

- **GIVEN** a decision with no `ApplyEvidenceRef`
- **WHEN** status is projected
- **THEN** `APPLY_CONFIRMED` MUST NOT be assigned

### Requirement: Experiment plan immutability and digest

`ExperimentPlan` revisions MUST be immutable once registered. `plan_digest` MUST equal
`sha256(canonical_json(B))` for canonical body **B** including reserved `switchback_schedule`.

#### Scenario: Plan revision preserves prior digest

- **GIVEN** revision 1 with digest D1
- **WHEN** revision 2 is registered
- **THEN** revision 1 MUST remain readable at digest D1

### Requirement: Orthogonal execution_state and outcome

`execution_state` MUST be independent of `outcome`. When `execution_state=ABORTED`
before terminal evaluation, projected `outcome` MUST remain `PENDING`.

#### Scenario: Evaluated with inconclusive outcome

- **GIVEN** evaluation completed under validity rules
- **WHEN** success/failure criteria are not met but validity permits terminal evaluation
- **THEN** `execution_state` MAY be `EVALUATED`
- **AND** `outcome` MAY be `INCONCLUSIVE` or `INVALID`

### Requirement: Outcome mapping vocabulary (demem_outcome_v1)

The foundation MUST define deterministic INVALID vs INCONCLUSIVE vs FAILED mapping
vocabulary (`ValidityReasonCode`, `project_outcome_from_validity` and related helpers).
Runtime evaluator enforcement is a future change.

#### Scenario: Integrity maps to INVALID not FAILED

- **GIVEN** `METRIC_DEFINITION_MISMATCH` in validity reasons
- **WHEN** outcome is projected via foundation mapping helpers
- **THEN** `outcome` MUST be `INVALID`
- **AND** MUST NOT be `FAILED`

### Requirement: Factual result vs interpretation boundary

`Interpretation` MUST NOT overwrite factual metric values, validity status,
deterministic outcome, or provenance at the domain API boundary.

#### Scenario: Interpretation append does not mutate factual result

- **GIVEN** an existing `FactualResult`
- **WHEN** an `Interpretation` is recorded
- **THEN** factual values and outcome MUST remain unchanged

### Requirement: Post-hoc vocabulary

`PostHocAnalysisRecord` MUST declare `analysis_kind` (`EXPLORATORY` | `POST_HOC`) and
MAY reference exploratory `MetricSpecRef` values not in the frozen plan. Post-hoc
records MUST NOT mutate frozen plan bytes, preregistered factual results, or
preregistered deterministic outcomes.

#### Scenario: Post-hoc does not rewrite frozen plan digest

- **GIVEN** a frozen plan digest D
- **WHEN** a `PostHocAnalysisRecord` is constructed
- **THEN** `plan_body_digest` for the frozen revision MUST remain D

### Requirement: Intervention signature determinism

`intervention_signature_digest` MUST be computed from structured normalized fields only;
free text MUST NOT be canonical similarity identity.

#### Scenario: Identical structured fields yield identical digest

- **GIVEN** two experiments with identical normalized intervention inputs
- **WHEN** digests are computed
- **THEN** digests MUST match

### Requirement: DecisionMemoryReader port vocabulary

The read port MUST declare `get_experiment_plan`, factual result access, similar
experiment search, and event listing contracts. Foundation delivers protocol types and
test fake only — not production projection stores.

#### Scenario: Test fake is not production store

- **GIVEN** `InMemoryDecisionMemoryRepository`
- **WHEN** module documentation is read
- **THEN** it MUST state test-only usage

### Requirement: Attribution fact set ref is optional vocabulary

`AttributionFactSetRef` MAY appear in types; foundation MUST NOT require live
attribution runtime.

#### Scenario: Slice A builds without attribution ingest

- **GIVEN** attribution runtime unavailable
- **WHEN** foundation unit tests run
- **THEN** they MUST pass without attribution ingestion
