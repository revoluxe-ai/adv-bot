# decision-experiment-memory

## ADDED Requirements

### Requirement: Decision memory does not duplicate authoritative payloads

The system MUST store semantics and immutable references (IDs, digests, tokens).
It MUST NOT copy full settings snapshots, ChangeSet bodies, or Apply receipt
payloads as SoT. Consumers resolve via `campaign-settings-history`, `ChangeSetV1`,
Apply Authority, and (when available) `attribution-facts-contract`.

#### Scenario: Decision view exposes refs not authoritative payloads

- **GIVEN** a persisted decision with settings and ChangeSet linkage refs
- **WHEN** a reader loads the decision view
- **THEN** the view MUST expose tokens and digests only
- **AND** MUST NOT embed authoritative settings or ChangeSet bodies as memory SoT

### Requirement: Independent decision and experiment identities

`DecisionMemoryRecord` MUST be keyed by `decision_id`. `ExperimentRecordV1` MUST
be keyed by `experiment_id` and MUST reference exactly one `decision_id`.
`experiment_id` MUST NOT be required to equal `decision_id` and equality MUST NOT
be a domain invariant.

#### Scenario: Distinct ids for one decision-experiment pair

- **GIVEN** a decision with `decision_id=D1` and an experiment with `experiment_id=E1`
- **WHEN** the experiment is persisted
- **THEN** `E1` MAY differ from `D1`
- **AND** the experiment MUST reference `decision_id=D1`

### Requirement: Decision to experiment cardinality

The domain contract MUST allow one decision to have zero or many experiments
(0..N). V1 creation APIs MAY restrict to 0..1 per decision, but types, events,
and reader contracts MUST remain compatible with 1:N without schema breaking changes.

#### Scenario: V1 single experiment restriction does not encode 1:1 in domain

- **GIVEN** a V1 writer that rejects a second experiment for the same decision
- **WHEN** the domain model is inspected
- **THEN** it MUST still model `decision_id` as a non-unique parent key for experiments

### Requirement: Decision without experiment

A `DecisionMemoryRecord` MAY exist without any `ExperimentRecordV1`. Experiments MUST NOT
be required to record decisions.

#### Scenario: Policy decision without measurable experiment

- **GIVEN** a human-recorded decision with rationale only
- **WHEN** the decision is persisted
- **THEN** a `DecisionMemoryRecord` MUST exist
- **AND** no `ExperimentRecordV1` is required

### Requirement: Treatment mode orthogonal to experiment design

Each experiment MUST declare `treatment_mode` of `LIVE` or `SHADOW` separately from
`experiment_design` (`RANDOMIZED_AB`, `SWITCHBACK`, `CONTROLLED_BEFORE_AFTER`,
`BEFORE_AFTER_OBSERVATIONAL`). `treatment_mode` MUST describe whether production
treatment is applied, not causal design type.

#### Scenario: Shadow observational study

- **GIVEN** `experiment_design=BEFORE_AFTER_OBSERVATIONAL` and `treatment_mode=SHADOW`
- **WHEN** a reader loads the experiment
- **THEN** causal evidence level MUST reflect observational design
- **AND** the experiment MUST NOT claim confirmed LIVE production exposure without evidence

### Requirement: Apply evidence reference without receipt payload

The domain MUST define optional `ApplyEvidenceRef` (or `ApplyReceiptRef`) as opaque
`apply_evidence_id` with optional `evidence_digest` and authority kind, without
embedding future Apply Authority receipt payloads.

#### Scenario: No apply evidence no apply confirmed

- **GIVEN** a decision with no linked `ApplyEvidenceRef`
- **WHEN** status is projected
- **THEN** `APPLY_CONFIRMED` MUST NOT be assigned

#### Scenario: No effective state evidence no confirmed live exposure

- **GIVEN** `treatment_mode=LIVE` and no authoritative effective-state evidence
- **WHEN** exposure is projected
- **THEN** confirmed LIVE `OBSERVING` MUST NOT be assigned
- **AND** `treatment_effective_from` MUST NOT be guessed

### Requirement: Slice A not blocked by Apply product type

Domain vocabulary and Slice A unit tests MUST NOT require an implemented Apply receipt
product type. `ApplyEvidenceRef` types and invariants suffice for Slice A.

#### Scenario: Slice A vocabulary without Apply Authority product type

- **GIVEN** only `ApplyEvidenceRef` types and projection invariants
- **WHEN** Slice A domain tests run
- **THEN** they MUST NOT require a concrete Apply receipt payload schema

### Requirement: Experiment requires ExperimentPlan

An `ExperimentRecord` MUST reference at least one immutable `ExperimentPlan`
revision. The system MUST NOT model experiments using only a flat
`evaluation_contract` field without plan identity (`plan_revision`, `plan_digest`).

#### Scenario: Plan registration creates immutable revision

- **GIVEN** a new experiment
- **WHEN** `PLAN_REGISTERED` is appended with `plan_revision=1` and body B
- **THEN** `plan_digest` MUST equal `sha256(canonical_json(B))`
- **AND** later events MUST NOT mutate revision 1 bytes

### Requirement: Plan freeze before outcome inspection

For `PREREGISTERED_CONFIRMATORY` experiments, the system MUST record `PLAN_FROZEN`
with a `frozen_plan_digest` before any preregistered outcome inspection or
terminal `SUCCEEDED`/`FAILED` assignment.

#### Scenario: Evaluation blocked without freeze

- **GIVEN** a confirmatory experiment without `PLAN_FROZEN`
- **WHEN** a preregistered evaluator run is requested
- **THEN** the run MUST be rejected or remain `outcome=PENDING`
- **AND** MUST NOT emit `SUCCEEDED` or `FAILED`

### Requirement: Plan revision and protocol deviation

Plan changes MUST append a new `plan_revision` or a `PROTOCOL_DEVIATION` event.
The system MUST NOT silently rewrite a prior plan revision.

#### Scenario: New revision preserves old digest

- **GIVEN** frozen plan digest D1 at revision 1
- **WHEN** revision 2 is registered
- **THEN** revision 1 MUST remain readable at digest D1

### Requirement: Preregistered vs post-hoc registration kinds

Each `ExperimentPlan` MUST declare `registration_kind` of
`PREREGISTERED_CONFIRMATORY` or `POST_HOC_EXPLORATORY`. Post-hoc conclusions MUST
remain distinguishable from preregistered outcomes in reader views and AI export.

#### Scenario: Post-hoc outcome distinguishable from preregistered

- **GIVEN** a preregistered confirmatory outcome and a separate post-hoc interpretation
- **WHEN** a reader loads experiment memory
- **THEN** post-hoc conclusions MUST be labeled distinct from preregistered terminal outcome

### Requirement: Orthogonal execution_state and outcome

`execution_state` MUST be independent of `outcome`. Allowed `execution_state`
values: `PLANNED`, `REGISTERED`, `APPLY_PENDING`, `APPLIED`, `OBSERVING`,
`EVALUATABLE`, `EVALUATED`, `ABORTED`. Allowed `outcome` values: `PENDING`,
`SUCCEEDED`, `FAILED`, `INCONCLUSIVE`, `INVALID`.

There is **no** `outcome=ABORTED` in V1. When `execution_state=ABORTED` before a
terminal evaluation run, projected `outcome` MUST remain `PENDING`.

#### Scenario: Evaluated with inconclusive outcome

- **GIVEN** an experiment with completed evaluation run
- **WHEN** validity or coverage fails success/failure criteria
- **THEN** `execution_state` MAY be `EVALUATED`
- **AND** `outcome` MUST be `INCONCLUSIVE` or `INVALID`
- **AND** MUST NOT be `SUCCEEDED` or `FAILED`

#### Scenario: Aborted execution leaves outcome pending

- **GIVEN** an experiment with `execution_state=ABORTED` before terminal evaluation
- **WHEN** outcome is projected
- **THEN** `outcome` MUST be `PENDING`
- **AND** MUST NOT introduce `outcome=ABORTED`

### Requirement: Validity gates block terminal success and failure

When required `data_validity` gates fail, the system MUST NOT set `outcome` to
`SUCCEEDED` or `FAILED`. It MUST set `INCONCLUSIVE` or `INVALID` per the
normative mapping below (`OUTCOME_MAPPING_VERSION`).

#### Scenario: Invalid exposure blocks success

- **GIVEN** `EXPOSURE_INTEGRITY_FAIL` in validity reasons
- **WHEN** evaluation runs
- **THEN** `outcome` MUST be `INVALID`
- **AND** MUST NOT be `SUCCEEDED` or `FAILED`

### Requirement: Deterministic INVALID vs INCONCLUSIVE outcome mapping

The evaluator MUST map terminal outcomes using versioned rules
(`OUTCOME_MAPPING_VERSION`, initial `demem_outcome_v1`). Free-text interpretation
MUST NOT select the mapping. Business underperformance MUST use `FAILED` only when
validity permits confirmatory comparison; evidence-integrity failures MUST NOT use
`FAILED`.

#### INVALID (evidence / contract integrity — evaluation not valid under frozen plan)

| Reason code | Terminal outcome |
|-------------|------------------|
| `SOURCE_INCOMPLETE` (required source missing beyond plan policy) | `INVALID` |
| `EXPOSURE_INTEGRITY_FAIL` | `INVALID` |
| `RECONCILIATION_FAILED` (when plan requires reconciliation) | `INVALID` |
| `METRIC_DEFINITION_MISMATCH` | `INVALID` |
| `MISSING_REQUIRED_INPUT` | `INVALID` |
| `STALE_OR_REVISED_SOURCE` (invalidates required evidence) | `INVALID` |
| Required plan `required_data_validity_conditions` hard-fail | `INVALID` |

#### INCONCLUSIVE (evaluation performed; cannot support SUCCEEDED or FAILED)

| Condition | Terminal outcome |
|-----------|------------------|
| Effect below/above threshold in neutral/indeterminate band per frozen success/failure criteria | `INCONCLUSIVE` |
| Insufficient precision / sample under `FIXED_HORIZON` stopping rule | `INCONCLUSIVE` |
| `OBSERVATION_WINDOW_INCOMPLETE` | `INCONCLUSIVE` |
| `SOURCE_COMPLETE_THROUGH_GAP` (data lag, not integrity break) | `INCONCLUSIVE` |
| `ATTRIBUTION_COVERAGE_LOW` when attribution optional but coverage insufficient for criteria | `INCONCLUSIVE` |
| `CONCURRENT_INTERVENTION` when policy marks indeterminate only | `INCONCLUSIVE` |

#### Scenario: Integrity maps to INVALID not FAILED

- **GIVEN** `METRIC_DEFINITION_MISMATCH` at evaluation time
- **WHEN** outcome is projected
- **THEN** `outcome` MUST be `INVALID`
- **AND** MUST NOT be `FAILED`

#### Scenario: Weak effect maps to INCONCLUSIVE not INVALID

- **GIVEN** validity permits evaluation and metrics are consistent
- **WHEN** observed effect lies in the plan-defined indeterminate region
- **THEN** `outcome` MUST be `INCONCLUSIVE`
- **AND** MUST NOT be `INVALID`

### Requirement: Assignment apply and exposure separation

The system MUST model separately: intended treatment, ChangeSet reference,
`ApplyEvidenceRef` (optional; no receipt payload owned here), resulting authoritative
state/version, `effective_from`, and `observation_start`. Decision creation MUST NOT
imply treatment assignment. ChangeSet creation MUST NOT imply apply. Apply evidence
MUST NOT imply observation start without `EXPOSURE_CONFIRMED`.

#### Scenario: Observation anchors to exposure not decision time

- **GIVEN** a decision recorded at T0 and exposure confirmed at T1 with burn-in
- **WHEN** observation window is computed
- **THEN** `observation_start` MUST be derived from exposure model
- **AND** MUST NOT default to T0 alone

#### Scenario: No observing without exposure

- **GIVEN** authoritative exposure cannot be established
- **WHEN** projection updates execution state
- **THEN** the experiment MUST NOT enter `OBSERVING` as valid evidence

### Requirement: Experiment design types and causal semantics

Each plan MUST declare `experiment_design` among: `RANDOMIZED_AB`, `SWITCHBACK`,
`CONTROLLED_BEFORE_AFTER`, `BEFORE_AFTER_OBSERVATIONAL`. The system MUST expose
`evidence_design` (same value as `experiment_design` for export stability) and
`causal_evidence_level` consistent with `experiment_design`. Designs MUST NOT claim
equivalent causal strength.

#### Scenario: Observational design capped evidence level

- **GIVEN** `experiment_design=BEFORE_AFTER_OBSERVATIONAL`
- **WHEN** an AI-readable view is produced
- **THEN** `causal_evidence_level` MUST indicate non-randomized observational strength
- **AND** narrative MUST NOT be stored as overriding that level

### Requirement: Explicit control and counterfactual

Every `ExperimentPlan` MUST include `control_definition` with explicit comparator
kind (randomized control, prior configuration, matched entity, historical baseline,
or reserved switchback control window). Comparison semantics MUST NOT be implicit.

#### Scenario: Control comparator is explicit

- **GIVEN** a registered `ExperimentPlan`
- **WHEN** the plan is read
- **THEN** `control_definition` MUST declare a comparator kind
- **AND** MUST NOT rely on implicit prose-only comparison

### Requirement: Data validity model and reason codes

The system MUST track `data_validity_status` in `VALID`, `PARTIAL`, `INVALID`,
`UNKNOWN` with machine-readable reason codes including at minimum:
`SOURCE_INCOMPLETE`, `SOURCE_COMPLETE_THROUGH_GAP`, `ATTRIBUTION_COVERAGE_LOW`,
`RECONCILIATION_FAILED`, `METRIC_DEFINITION_MISMATCH`, `EXPOSURE_INTEGRITY_FAIL`,
`MISSING_REQUIRED_INPUT`, `OBSERVATION_WINDOW_INCOMPLETE`, `CONCURRENT_INTERVENTION`,
`STALE_OR_REVISED_SOURCE`.

#### Scenario: Validity reason codes are machine-readable

- **GIVEN** an evaluation run records validity
- **WHEN** a reader inspects the validity snapshot
- **THEN** at least one reason code from the required set MUST be present when not VALID

### Requirement: Versioned metric definitions

Experiment plans and factual results MUST reference metrics by `metric_id` and
`metric_definition_version` with source family, grain, scope, numerator/denominator
semantics, coverage requirements, analysis window, evaluation cutoff, and
`source_complete_through`. Numeric results MUST NOT use bare metric names alone.

#### Scenario: Incomparable metrics flagged

- **GIVEN** two results with same metric name but different `metric_definition_version`
- **WHEN** comparability is checked
- **THEN** the system MUST report them as not semantically comparable

### Requirement: Window model fields

Experiment windows MUST model explicitly: baseline start/end, treatment
effective_from, burn-in/out, observation start/end, evaluation_cutoff,
source_complete_through, evaluated_at, and timezone. Windows MUST NOT be derived
solely from decision timestamps.

#### Scenario: Windows not derived from decision time alone

- **GIVEN** a decision recorded at T0 and exposure confirmed later
- **WHEN** observation window is computed
- **THEN** `observation_start` MUST use exposure/window model fields
- **AND** MUST NOT equal T0 by default

### Requirement: Concurrent intervention references

Material concurrent changes during an experiment MUST be recordable as structured
confounder events (price, stock, budget, overlapping experiment, etc.). Confounders
MUST be machine-readable and MAY affect validity without automatic invalidation of
all experiments.

#### Scenario: Confounder event is structured

- **GIVEN** a concurrent budget change during an experiment
- **WHEN** a confounder is recorded
- **THEN** a structured `CONFOUNDER_DETECTED` event MUST be appendable with typed reason

### Requirement: Intervention signature for similarity

The system MUST compute deterministic `intervention_signature` from normalized
setting keys, old/new values or deltas, scope, affected entities, control mode, and
ChangeSet semantic digest when available. Free text MUST NOT be canonical similarity
identity. Vector similarity MAY be offered only as secondary non-authoritative retrieval.

#### Scenario: Similarity uses structured digest

- **GIVEN** two experiments with identical normalized intervention fields
- **WHEN** similarity search runs
- **THEN** primary match MUST use `intervention_signature` digest equality

### Requirement: Analysis method and stopping rule frozen in plan

`ExperimentPlan` MUST include `analysis_method`, `stopping_rule`, and
`analysis_config_version`. Stopping criteria MUST NOT change after outcomes exist
except via new plan revision or `PROTOCOL_DEVIATION`.

#### Scenario: Stopping rule frozen after outcome exists

- **GIVEN** a terminal preregistered outcome exists for a frozen plan digest
- **WHEN** a writer attempts to change `stopping_rule` without new plan revision
- **THEN** the change MUST be rejected or recorded only as `PROTOCOL_DEVIATION`

### Requirement: Factual result vs interpretation boundary

`FactualResult` MUST be produced only by deterministic evaluators/readers.
`Interpretation` MAY contain AI/human narrative. Interpretation MUST NOT overwrite
factual metric values, validity status, deterministic outcome, or provenance.

#### Scenario: Interpretation append does not mutate factual result

- **GIVEN** an existing `FactualResult` for an evaluation run
- **WHEN** an interpretation event is appended
- **THEN** factual metric values and outcome MUST remain unchanged

### Requirement: Evaluation provenance and reproducibility

Each evaluation run MUST retain immutable refs: schema version, frozen plan digest,
AI Package id/digest, snapshot refs, settings state_token, ChangeSet semantic digest,
receipt refs, metric definition versions, analysis config version, evaluation input
refs, producer version, and evaluation run digest.

#### Scenario: Evaluation run carries provenance refs

- **GIVEN** a completed evaluation run
- **WHEN** provenance is read
- **THEN** `frozen_plan_digest` and `evaluation_run_digest` MUST be present

### Requirement: Post-hoc analysis distinguishable

Post-hoc or exploratory analyses MUST be marked `POST_HOC` or `EXPLORATORY`, MUST
NOT modify frozen preregistered plan bytes, and MUST store conclusions as separate
interpretations distinguishable from preregistered outcomes.

#### Scenario: Post-hoc does not rewrite frozen plan

- **GIVEN** a frozen preregistered plan digest
- **WHEN** a post-hoc analysis is recorded
- **THEN** frozen plan revision bytes MUST remain unchanged

### Requirement: Attribution facts as optional future evidence

When `attribution-facts-contract` is available in the deployed environment, evaluation
MAY reference `attribution_fact_set_ref`. When unavailable, validity MUST degrade
(e.g. `UNKNOWN` or `ATTRIBUTION_COVERAGE_LOW`) and MUST NOT block decision-memory
vocabulary-only work. Decision memory Slice A MUST NOT hard-depend on attribution
runtime on current `stage`.

#### Scenario: Missing attribution degrades validity without blocking Slice A vocabulary

- **GIVEN** attribution facts are not deployed
- **WHEN** Slice A domain vocabulary is built
- **THEN** types and tests MUST NOT require live attribution fact ingestion

### Requirement: DecisionMemoryReader and AI export index

The read port MUST support experiment plans, factual results, similar experiments by
intervention signature, and a compact `experiment_memory_index` for AI retrieval
(what was tried, where, why, signature, design, validity, outcome, similar prior,
immutable refs) without prose-primary storage.

Future `decision_memory_v1` MUST include: `recent_decisions`, `active_experiments`,
`recent_experiment_results`, `experiment_memory_index`.

#### Scenario: Reader lists observing experiments

- **GIVEN** two experiments in `OBSERVING` for the same shop
- **WHEN** `list_observing_experiments` is called
- **THEN** both MUST be returned with execution/outcome projections

### Requirement: Append-only events and idempotency

Events remain append-only. Receipt and evaluation run ingestion MUST be idempotent.
Decision memory MUST NOT perform production writes or authorize apply.

#### Scenario: Duplicate apply evidence ingest is idempotent

- **GIVEN** an `ApplyEvidenceRef` already linked to a decision
- **WHEN** the same evidence id is ingested again
- **THEN** the store MUST NOT create a duplicate decision record
