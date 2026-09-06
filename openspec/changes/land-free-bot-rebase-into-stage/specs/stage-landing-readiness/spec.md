## ADDED Requirements

### Requirement: Branch landing readiness is scope-bounded

Merge readiness MUST be calculated from one declared target-base reference, one
candidate snapshot and one explicit set of in-scope changes. The evidence MUST
record the target-base and candidate identities, and unrelated dirty worktree
state MUST NOT change the verdict.

#### Scenario: Candidate snapshot changes during verification

- **GIVEN** readiness evidence was collected for a declared candidate snapshot
- **WHEN** the candidate identity or in-scope change set changes
- **THEN** the previous readiness verdict is invalidated
- **THEN** verification MUST be repeated before merge is considered ready

#### Scenario: Unrelated dirty state is present

- **GIVEN** unrelated changes exist outside the declared landing scope
- **WHEN** the merge checks are evaluated
- **THEN** those changes are excluded from the evidence
- **THEN** the readiness result identifies the excluded state without treating it
  as part of the candidate

### Requirement: Migration provenance gates route selection

The landing evidence MUST distinguish remote-history reachability, reachability
from the landing base, and proven database application. Remote reachability
alone MUST NOT be treated as proof that a migration was applied in a database.

#### Scenario: Database application is proven

- **GIVEN** a migration is proven to have been applied outside the candidate
  branch
- **WHEN** the merge route is selected
- **THEN** the existing migration history is preserved
- **THEN** any correction MUST use a new forward repair or compatibility step

#### Scenario: Database application is not proven

- **GIVEN** a migration is reachable from a remote feature branch
- **AND** no database or deployment evidence proves its application
- **WHEN** the merge route is selected
- **THEN** the evidence records application as unproven
- **THEN** rewriting the not-yet-landed candidate migration MAY be considered
  only after explicit provenance review

#### Scenario: Provenance evidence conflicts

- **GIVEN** available provenance sources disagree or leave application status
  unknown
- **WHEN** readiness is evaluated
- **THEN** the result MUST contain `EVIDENCE_GAP`
- **THEN** merge readiness MUST be `NO_GO`

### Requirement: Migration route preserves forward-only history

Landing MUST preserve every migration revision proven to be published or
applied. A topology-only convergence step MUST NOT contain schema or data
changes. A schema/data transition MUST be represented by a dedicated
forward-only rollout route.

#### Scenario: Topology-only convergence is checked

- **GIVEN** the candidate contains a step whose purpose is only to converge
  migration heads
- **WHEN** the migration graph is verified
- **THEN** the step has one or more required parents and no schema/data
  operation
- **THEN** existing revisions remain unchanged

#### Scenario: Published migration requires correction

- **GIVEN** the candidate migration is proven to be published or applied
- **WHEN** a defect or unsafe transition is found
- **THEN** the original revision is not rewritten
- **THEN** readiness remains `NO_GO` until a forward repair route is specified
  and verified

### Requirement: Data transition semantics are explicitly verified

Before readiness, the transition MUST state the expected values for existing
and newly created records, the nullability sequence, retry behavior and the
recovery action. The evidence MUST include a preview of affected records and
an explicit confirmation by the migration rollout owner.

#### Scenario: Existing and new record behavior is compatible

- **GIVEN** a migration introduces a field with a data transition
- **WHEN** the transition is verified on the test database
- **THEN** the preview reports the affected-record count and pre-transition
  value distribution
- **THEN** existing-record results, new-record defaults and final constraint
  behavior match the declared semantics

#### Scenario: Transition is retried after an interrupted run

- **GIVEN** the transition is interrupted after a partial operation
- **WHEN** the same rollout is retried
- **THEN** already processed records are not corrupted or assigned a second
  incompatible result
- **THEN** the final state remains compatible with the declared constraint

#### Scenario: Legacy records use the paid-state classifier

- **GIVEN** an existing record is included in the one-time release transition
- **WHEN** its `bot_active` state is evaluated
- **THEN** `bot_active=True` results in `auto_update_minus_phrases=True`
- **THEN** `bot_active=False` results in `auto_update_minus_phrases=False`
- **THEN** new records receive `auto_update_minus_phrases=False`
- **THEN** a persistent `None → True` runtime fallback is not used

#### Scenario: Affected-record preview is missing

- **GIVEN** a schema/data transition is proposed
- **WHEN** no affected-record preview or owner confirmation is available
- **THEN** readiness MUST be `NO_GO`
- **THEN** the transition MUST NOT be represented as safely verified

### Requirement: Existing client behavior remains compatible

Landing MUST preserve the effective behavior of existing paid and free clients.
The compatibility check MUST cover automation flags, billing behavior, WB
write activity and campaign lifecycle. A migration that changes any of these
for existing clients MUST be treated as an intentional behavior change, not as
a neutral schema default.

#### Scenario: Existing client baseline is preserved

- **GIVEN** paid and free client baselines are captured before the migration
- **WHEN** the candidate migration is applied on the test database
- **THEN** effective automation, billing, WB write and campaign lifecycle
  behavior remains unchanged unless explicitly declared by an accepted decision
- **THEN** the before/after comparison is included in readiness evidence

#### Scenario: Backfill enables previously disabled automation

- **GIVEN** a backfill changes a previously disabled automation flag for existing
  client records
- **WHEN** no accepted product decision and rollout evidence authorize that
  behavior change
- **THEN** readiness MUST be `NO_GO`
- **THEN** the migration MUST NOT be presented as backward-compatible

#### Scenario: Paid and free cohorts remain separated

- **GIVEN** the candidate affects records from paid and free client cohorts
- **WHEN** compatibility checks are evaluated
- **THEN** each cohort is compared with its own baseline
- **THEN** the migration MUST NOT transfer paid automation behavior into free
  clients or change billing/lifecycle behavior implicitly

#### Scenario: Compatibility recovery is required

- **GIVEN** a partial transition creates client behavior drift
- **WHEN** recovery is evaluated
- **THEN** the evidence identifies affected clients and the recovery action
- **THEN** readiness remains `NO_GO` until the drift is removed or explicitly
  approved as a product behavior change

### Requirement: Required quality gates are fail-closed

Readiness MUST require a converged migration graph, passing migration safety
checks, passing data-transition regression checks and passing required targeted,
unit, static and OpenSpec checks. Every result MUST refer to the same candidate
snapshot.

#### Scenario: All gates pass for one snapshot

- **GIVEN** graph, safety, data-transition and required quality checks pass
- **AND** all evidence refers to the declared candidate snapshot
- **WHEN** readiness is evaluated
- **THEN** the result is `GO`
- **THEN** the evidence lists each executed gate and its result

#### Scenario: Any required gate fails

- **GIVEN** at least one required gate fails or is not executed
- **WHEN** readiness is evaluated
- **THEN** the result is `NO_GO`
- **THEN** the failed or missing gate is named as an actionable gap

#### Scenario: A check uses a different snapshot

- **GIVEN** a check result was produced for a different candidate identity
- **WHEN** results are assembled
- **THEN** that result cannot satisfy the corresponding gate
- **THEN** readiness remains `NO_GO` until the check is replayed

### Requirement: Merge readiness does not claim owner-owned deployment

Merge-readiness evidence MUST remain separate from image build, Harbor upload,
deployment restart, pod startup, stage/prod smoke and post-deploy verification.
A merge-readiness `GO` MUST authorize only the safe merge decision for the
declared target branch; it MUST NOT claim that any later operational action
occurred.

#### Scenario: Merge readiness is green

- **GIVEN** all in-scope graph, migration, compatibility, static and OpenSpec
  checks pass for one candidate snapshot
- **WHEN** merge readiness is issued
- **THEN** the evidence identifies safe merge into the declared target branch
- **THEN** image rollout and all deployment verification are identified as
  owner-owned next steps outside this change

#### Scenario: Deployment evidence is absent

- **GIVEN** merge-readiness checks are complete
- **WHEN** image, Harbor, deployment, pod or post-deploy evidence is absent
- **THEN** merge readiness is not downgraded solely for that absence
- **THEN** the evidence MUST state that those operational receipts are deferred
  and are not claimed by this change
