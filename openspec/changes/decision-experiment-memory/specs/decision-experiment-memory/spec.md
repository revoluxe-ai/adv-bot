# decision-experiment-memory

## ADDED Requirements

### Requirement: Decision and experiment identities are independent

The system MUST persist `decision_id` and `experiment_id` as independent opaque
identifiers. An experiment MUST reference exactly one `decision_id`. A decision
MUST support zero or more experiments over time. The system MUST NOT require
`experiment_id` to equal `decision_id`.

#### Scenario: Follow-up experiment shares decision

- **GIVEN** a decision `D1` with a completed experiment `E1`
- **WHEN** a follow-up experiment `E2` is created for the same decision context
- **THEN** `E2.decision_id` equals `D1`
- **AND** `E2.experiment_id` differs from `E1.experiment_id`

#### Scenario: Decision without experiment

- **WHEN** only decision semantics are recorded
- **THEN** no experiment record is required
- **AND** decision outcome is not applicable at experiment granularity

### Requirement: Experiment design is separate from treatment mode

`experiment_design` MUST describe how evidence is produced. `treatment_mode`
MUST describe whether production intervention is live. `SHADOW` MUST be expressed
only as `treatment_mode`, not as `experiment_design`.

#### Scenario: Shadow counterfactual

- **WHEN** an experiment uses `treatment_mode=SHADOW`
- **THEN** `experiment_design` MAY be `BEFORE_AFTER_OBSERVATIONAL`
- **AND** the system MUST NOT claim LIVE production exposure

### Requirement: Preregistered plan freezes by digest

An experiment plan MUST be registered with monotonic `plan_revision` and
`plan_digest`. After registration, that revision MUST NOT be silently mutated.
Amendments MUST create a new revision and digest.

#### Scenario: Plan amendment bumps revision

- **GIVEN** plan revision 1 is registered
- **WHEN** success criteria change
- **THEN** revision becomes 2
- **AND** `plan_digest` changes
- **AND** revision 1 remains auditable

### Requirement: Apply evidence is optional for domain vocabulary

The domain model MUST include `ApplyEvidenceRef` without requiring a concrete
Apply receipt payload. Slice A vocabulary MUST be usable while Apply Authority
is absent.

#### Scenario: Decision without apply confirmation

- **GIVEN** no BOUND Apply evidence
- **WHEN** a decision is otherwise complete
- **THEN** decision execution MUST NOT be `APPLY_CONFIRMED`
- **AND** LIVE `effective_from` MUST NOT be established from Apply

#### Scenario: LIVE exposure requires apply binding

- **GIVEN** `treatment_mode=LIVE`
- **WHEN** Apply evidence is not BOUND
- **THEN** the experiment MUST NOT claim valid LIVE exposure
- **AND** outcome MUST NOT be `SUCCEEDED` or `FAILED` based on guessed execution

### Requirement: Execution state and outcome are orthogonal

Experiment `execution_state` MUST be independent of `outcome`. Terminal
evaluation MUST allow `execution_state=EVALUATED` with `outcome=INVALID` or
`outcome=INCONCLUSIVE`.

#### Scenario: Evaluated but invalid

- **GIVEN** validity assessment is `INVALID`
- **WHEN** evaluation completes
- **THEN** `execution_state` is `EVALUATED`
- **AND** `outcome` is `INVALID`

#### Scenario: Evaluated inconclusive

- **GIVEN** observation window ended with partial metrics
- **WHEN** evaluation completes
- **THEN** `execution_state` is `EVALUATED`
- **AND** `outcome` is `INCONCLUSIVE`

### Requirement: Outcomes are factual not narrative

`outcome` MUST be derived from registered criteria and validity rules.
Narrative explanation MUST NOT be the sole source of `outcome`.

#### Scenario: Insufficient evidence

- **WHEN** required metrics are missing at evaluation cutoff
- **THEN** `outcome` is `INCONCLUSIVE`
- **AND** not `FAILED` solely due to missing data

### Requirement: External authorities are referenced not copied

Decision and experiment records MUST reference settings history, ChangeSet
digests, Apply evidence, attribution, and AI Package using immutable IDs or
digests. They MUST NOT duplicate authoritative payloads.

#### Scenario: Settings evidence pointer

- **WHEN** recording pre-intervention settings
- **THEN** the record stores `snapshot_id` and `state_hash`
- **AND** does not embed full settings JSON as SoT

### Requirement: Memory does not grant write authority

Creating or updating decision/experiment memory MUST NOT authorize production
writes. Apply Authority remains the only production write gate.

#### Scenario: Recorded decision is non-authoritative for write

- **WHEN** a decision links a ChangeSet
- **THEN** memory update alone MUST NOT trigger Apply or WB writes
