## ADDED Requirements

### Requirement: Apply Authority is sole production write gate

Only WB Sky Apply Authority MAY authorize production writes for in-scope
`ChangeSetV1` apply operations. AI, MCP, REST, Telegram, and dry-run MUST NOT
invoke production settings writers or WB mutation adapters directly for the same
mutation domain.

#### Scenario: Unauthorized actor does not invoke writer (S06)

- **GIVEN** an `ApplyRequestV1` whose principal lacks shop/campaign authorization
- **WHEN** Apply Authority processes the request
- **THEN** execution status MUST be `REJECTED` with `UNAUTHORIZED`
- **AND** no production writer adapter MUST be invoked

#### Scenario: MCP cannot invoke writer directly (S16)

- **GIVEN** an MCP tool attempt to call a production WB or PG settings writer
  without going through Apply Authority
- **WHEN** the call is evaluated against architecture policy
- **THEN** the path MUST be forbidden
- **AND** Apply Authority MUST remain the only allowed write gate

### Requirement: Dry-run success is not apply permission

`DryRunResultV1` with status `OK` MUST NOT cause production writes without a
separate Apply Authority decision. Apply MUST re-validate at execution time.

#### Scenario: Exact dry-run-bound apply succeeds (S01)

- **GIVEN** a persisted `DryRunReceiptV1` for status `OK` with matching `sd1` and `pd1`
- **AND** an `ApplyRequestV1` with the same `ChangeSetV1` body and binding digests
- **AND** authoritative `st1` tokens still match operation preconditions
- **AND** an authorized principal
- **WHEN** Apply Authority executes V1 PG policy apply
- **THEN** terminal status MUST be `VERIFIED`
- **AND** immutable `ApplyEvidenceV1` MUST be recorded

### Requirement: Dry-run binding integrity

Apply MUST bind to the exact reviewed semantic mutation. Server MUST recompute
`semantic_digest` and `preview_digest` and MUST NOT trust client values without
equality check against receipt and fresh validation.

#### Scenario: ChangeSet digest differs from bound plan (S07)

- **GIVEN** an `ApplyRequestV1` whose `changeset` body yields a different `sd1`
  than `dry_run_binding.semantic_digest`
- **WHEN** Apply Authority validates binding
- **THEN** status MUST be `REJECTED` with `CHANGESET_DIGEST_MISMATCH`
- **AND** no writer MUST be invoked

### Requirement: Stale state rejection

If authoritative campaign settings changed after dry-run such that `st1`
`state_token` no longer matches operation preconditions, Apply MUST fail closed
before write.

#### Scenario: state_token changed after dry-run (S02)

- **GIVEN** dry-run succeeded with token `st1_A`
- **AND** authoritative state now yields `st1_B` for the same resource projection
- **WHEN** Apply Authority validates concurrency
- **THEN** status MUST be `REJECTED` with `STALE_STATE`
- **AND** no PG settings mutation MUST commit

### Requirement: Idempotency

Apply MUST persist idempotency keyed by `(scope.shop_id, idempotency_key)` and
`semantic_digest`.

#### Scenario: Same idempotency key and same request replays evidence (S03)

- **GIVEN** a completed `VERIFIED` apply for `(shop, key)` and `sd1_X`
- **WHEN** an identical `ApplyRequestV1` is submitted again
- **THEN** Apply Authority MUST return the existing `ApplyEvidenceV1`
- **AND** MUST NOT perform a duplicate PG write

#### Scenario: Same key different semantic request conflicts (S04)

- **GIVEN** a prior apply record for `(shop, key)` bound to `sd1_X`
- **WHEN** a new request arrives with the same key and `sd1_Y` where `Y ≠ X`
- **THEN** status MUST be `IDEMPOTENCY_CONFLICT`
- **AND** no write MUST occur

### Requirement: Capability revalidation at apply

Apply MUST re-evaluate capabilities at execution time. Unknown or unsupported
capability MUST fail closed.

#### Scenario: Unsupported capability at apply time (S05)

- **GIVEN** dry-run passed when capability was eligible
- **AND** at apply time the same required capability evaluates to `UNKNOWN` or ineligible
- **WHEN** Apply Authority validates capabilities
- **THEN** status MUST be `REJECTED` with `CAPABILITY_DRIFT`
- **AND** no writer MUST be invoked

### Requirement: PG settings transaction atomicity (V1)

For V1 internal PG-only policy mutations in one shop, all plan steps MUST commit
in a single PostgreSQL transaction or roll back entirely.

#### Scenario: Setting-only internal transaction succeeds atomically (S08)

- **GIVEN** an authorized apply with two valid policy operations on distinct resources
- **WHEN** Apply Authority executes the PG writer
- **THEN** both mutations MUST be visible after commit
- **AND** partial commit MUST NOT occur

#### Scenario: Internal validation failure causes zero writes (S09)

- **GIVEN** an apply request that fails validation before `APPLYING`
- **WHEN** Apply Authority completes
- **THEN** no `AdvSetting` policy fields MUST change
- **AND** status MUST be `REJECTED` or `FAILED` before writer acceptance

### Requirement: External writer failure taxonomy

When external WB writers are introduced (out of V1 scope), rejection and unknown
outcomes MUST be recorded distinctly.

#### Scenario: External writer rejection recorded as failure (S10)

- **GIVEN** an apply plan step that calls an external WB writer (future slice)
- **AND** the writer returns a definitive rejection before acceptance
- **WHEN** Apply Authority records the outcome
- **THEN** execution status MUST be `FAILED` with `WRITER_REJECTED`
- **AND** MUST NOT be reported as `VERIFIED`

#### Scenario: Unknown WB result is UNKNOWN_EXTERNAL_STATE (S11)

- **GIVEN** a writer call that may have reached WB but returned timeout/ambiguous error
- **WHEN** Apply Authority cannot prove whether the mutation was accepted
- **THEN** status MUST be `UNKNOWN_EXTERNAL_STATE`
- **AND** Apply Authority MUST NOT automatically retry the external write

### Requirement: Post-apply verification

After write, Apply Authority MUST reread canonical authoritative settings state
and MUST distinguish write acceptance from verified desired state.

#### Scenario: Post-write reread matches intended state (S12)

- **GIVEN** a committed PG policy apply
- **WHEN** verification re-reads `local_policy` via authoritative resolver
- **THEN** normalized desired fields MUST equal authoritative values
- **AND** terminal status MUST be `VERIFIED`

#### Scenario: Post-write reread mismatch is not VERIFIED (S13)

- **GIVEN** a PG commit succeeded at driver level
- **AND** verification read shows a differing normalized value
- **WHEN** Apply Authority completes verification
- **THEN** status MUST NOT be `VERIFIED`
- **AND** failure code MUST be `VERIFICATION_MISMATCH`

#### Scenario: New state_token after verified apply (S14)

- **GIVEN** a `VERIFIED` apply
- **WHEN** evidence is finalized
- **THEN** `ApplyEvidenceV1` MUST include `post_state_tokens` computed via `st1`
- **AND** `post_state_tokens` MUST differ from `pre_state_tokens` when mutations occurred

### Requirement: Transport parity

REST and MCP Apply entrypoints MUST call the same Apply Authority application
service with identical semantics.

#### Scenario: REST and MCP use same Apply service (S15)

- **GIVEN** equivalent `ApplyRequestV1` payloads from REST and MCP transports
- **WHEN** each invokes Apply Authority
- **THEN** validation, idempotency, and outcomes MUST be identical
- **AND** transport channel MUST affect audit metadata only

### Requirement: Immutable apply evidence

`ApplyEvidenceV1` MUST be append-only authoritative execution evidence owned by
Apply Authority, not by decision experiment memory.

#### Scenario: Apply receipt is immutable evidence (S17)

- **GIVEN** a finalized `ApplyEvidenceV1`
- **WHEN** any consumer attempts to mutate stored evidence
- **THEN** the store MUST forbid updates that change execution facts
- **AND** only append-only audit linkage MAY be added in separate tables if needed

### Requirement: Campaign settings history boundary

`campaign_settings_history` remains the authority for historical settings
snapshots over time. Apply evidence MAY reference history snapshot ids but MUST
NOT replace history SoT.

#### Scenario: History remains separate authority (S18)

- **GIVEN** a verified apply
- **WHEN** history collector records a new settings snapshot
- **THEN** history MUST remain owned by `campaign_settings_history`
- **AND** Apply evidence MUST NOT be the sole record of historical settings state

### Requirement: Decision memory boundary

Decision experiment memory MAY reference `apply_id` but MUST NOT own apply
execution evidence.

#### Scenario: Decision memory references evidence only (S19)

- **GIVEN** an external decision memory record
- **WHEN** it links to an apply outcome
- **THEN** it MUST reference `ApplyEvidenceV1.apply_id`
- **AND** MUST NOT be the canonical store of execution status or post-state tokens

### Requirement: Unknown operation or contract version fails closed

Unsupported `contract_version`, unknown operation types, or schema mismatch MUST
reject apply without writer invocation.

#### Scenario: Unknown operation version fails closed (S20)

- **GIVEN** an `ApplyRequestV1` with unsupported `contract_version` or a ChangeSet
  operation outside the V1 bounded set
- **WHEN** Apply Authority validates
- **THEN** status MUST be `REJECTED`
- **AND** no writer MUST be invoked
