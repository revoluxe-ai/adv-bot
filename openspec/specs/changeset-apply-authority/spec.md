# changeset-apply-authority Specification

## Purpose

WB Sky **Apply Authority** for bounded `ChangeSetV1` **PG policy** mutations:
transport-independent apply contract, dry-run receipt binding, idempotency,
durable evidence, and single-transaction PG writes via
`pg.campaign_settings_policy_v1`. External WB mutation and REST/MCP Apply
transports are **not** part of this spec's delivered V1 surface (see evolution
doc below).

Implemented V1 (Slices A–C): three `campaign.set_*_policy` operations, one
PostgreSQL transaction per apply. Future WB/transport/cross-link work is
documented in
`openspec/evolution/changeset-apply-authority-future-boundaries.md` only.

## Requirements

### Requirement: Apply Authority is sole production write gate (V1 PG path)

Only WB Sky Apply Authority MAY authorize production writes for in-scope
`ChangeSetV1` apply operations in V1. Dry-run MUST NOT invoke production
settings writers. The V1 registered writer adapter is
`pg.campaign_settings_policy_v1` only.

#### Scenario: Unauthorized actor does not invoke writer (S06)

- **GIVEN** an `ApplyInvocationContext` whose server-resolved principal lacks shop authorization
- **WHEN** Apply Authority processes `apply(request, context)`
- **THEN** terminal status MUST be `REJECTED` with reason `UNAUTHORIZED`
- **AND** no production writer adapter MUST be invoked

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

Apply MUST persist idempotency keyed by `(scope.shop_id, idempotency_key)`.
Replay fingerprint MUST be `apply_contract_version` + `semantic_digest` (`sd1`) +
`preview_digest` (`pd1`). Same key with different fingerprint MUST conflict.

#### Scenario: Same idempotency key and same request replays evidence (S03)

- **GIVEN** a completed `VERIFIED` apply for `(shop, key)` with fingerprint F
  (`apply_v1` + `sd1_X` + `pd1_X`)
- **WHEN** an authorized caller submits the same fingerprint F again
- **THEN** Apply Authority MUST return the existing `ApplyEvidenceV1`
- **AND** MUST NOT perform a duplicate PG write

#### Scenario: Same key different semantic request conflicts (S04)

- **GIVEN** a prior apply record for `(shop, key)` bound to fingerprint F1
- **WHEN** a new request arrives with the same key and fingerprint F2 where `F2 ≠ F1`
  (including different `sd1` or `pd1` or `apply_contract_version`)
- **THEN** terminal status MUST be `REJECTED` with reason `IDEMPOTENCY_CONFLICT`
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

### Requirement: Immutable apply evidence

`ApplyEvidenceV1` MUST be append-only authoritative execution evidence owned by
Apply Authority, not by decision experiment memory.

#### Scenario: Apply receipt is immutable evidence (S17)

- **GIVEN** a finalized `ApplyEvidenceV1` persisted through Apply Authority repositories
- **WHEN** Apply Authority persistence APIs are used after terminal insert
- **THEN** execution facts on the evidence row MUST NOT be updated in place
- **AND** privileged raw SQL `UPDATE`/`DELETE` outside repository APIs is not claimed as DB-enforced immutability in V1

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

### Requirement: Trusted invocation context

Client `ApplyRequestV1` MUST NOT carry authoritative principal, shop access proof,
or permission grants. Transports MUST supply `ApplyInvocationContext` built from
authenticated session. Fabricated principal or grants in request JSON MUST NOT
authorize apply.

#### Scenario: Untrusted request fields cannot self-authorize (S21)

- **GIVEN** an `ApplyRequestV1` embedding forged `principal_ref` or `capability_grants`
- **WHEN** Apply Authority validates using only server `ApplyInvocationContext`
- **THEN** forged fields MUST be ignored for authorization
- **AND** apply MUST fail closed unless real context authorizes the shop

### Requirement: Idempotent replay authorization

Returning stored `ApplyEvidenceV1` for an idempotency hit MUST require current
caller authorization to the shop and evidence; unauthorized replay MUST NOT disclose
prior evidence.

#### Scenario: Idempotent replay requires authorization (S22)

- **GIVEN** a prior `VERIFIED` apply for `(shop_id, idempotency_key)`
- **AND** a new call with the same fingerprint but an unauthorized `ApplyInvocationContext`
- **WHEN** Apply Authority handles the request
- **THEN** terminal status MUST be `REJECTED` with reason `UNAUTHORIZED`
- **AND** MUST NOT return the prior `ApplyEvidenceV1` payload

### Requirement: Dry-run receipt lifecycle

`DryRunReceiptV1` MUST be server-issued from dry-run execution, persisted by
`DryRunReceiptStore`, and lifecycle-managed independently of transport.

#### Scenario: Consumed receipt cannot authorize second apply (S23)

- **GIVEN** a `DryRunReceiptV1` in `CONSUMED` state after a verified apply
- **WHEN** a new distinct apply is attempted with the same receipt id
- **THEN** status MUST be `REJECTED` with `RECEIPT_INVALID`
- **AND** no writer MUST be invoked

#### Scenario: Pre-write rejection does not consume receipt (S24)

- **GIVEN** a receipt in `ISSUED` state
- **WHEN** apply fails with a rolled-back pre-write error other than stale/drift/mismatch invalidation
- **THEN** receipt MUST NOT transition to `CONSUMED`
- **AND** claim MUST be released back to `ISSUED` when applicable

### Requirement: Attempt lifecycle separate from immutable evidence

`ApplyAttemptRecord` MAY transition through non-terminal states. `ApplyEvidenceV1`
MUST be insert-only at terminal `VERIFIED` and MUST NOT be updated in place across
lifecycle states.

#### Scenario: Evidence immutability vs attempt lifecycle (S25)

- **GIVEN** an apply moving from `APPLYING` to `VERIFYING`
- **WHEN** lifecycle state updates occur
- **THEN** no existing `ApplyEvidenceV1` row MAY be mutated
- **AND** evidence insertion MUST occur only at terminal commit boundary

### Requirement: PG settings and evidence atomicity (V1)

For V1 PG-only apply, settings mutations, verification, idempotency terminal
state, receipt consumption, and `ApplyEvidenceV1` persistence MUST commit in one
PostgreSQL transaction. Client-visible `VERIFIED` MUST NOT be returned before
COMMIT succeeds.

#### Scenario: Settings and evidence commit atomically (S26)

- **GIVEN** a successful in-txn verification
- **WHEN** the database transaction commits
- **THEN** both policy mutations and `ApplyEvidenceV1` MUST be durable
- **AND** partial durability (settings without evidence) MUST NOT be labeled `VERIFIED`

### Requirement: Unknown internal commit

`UNKNOWN_INTERNAL_COMMIT` MUST be reserved for ambiguous commit acknowledgement,
not ordinary rolled-back validation or writer errors.

#### Scenario: Lost commit acknowledgement (S27)

- **GIVEN** a PG apply where commit outcome is unknown after connection loss
- **WHEN** Apply Authority cannot determine whether the transaction committed
- **THEN** status MUST be `UNKNOWN_INTERNAL_COMMIT`
- **AND** automatic duplicate mutation MUST NOT be attempted without idempotency reconciliation

### Requirement: Authorization distinct from domain capability

Unauthorized principals MUST receive `UNAUTHORIZED`. Ineligible or unknown domain
capabilities MUST receive `CAPABILITY_DRIFT` without conflating the two.

#### Scenario: Authorization vs capability distinction (S28)

- **GIVEN** an authorized principal for the shop
- **AND** a required domain capability evaluates to `UNKNOWN` at apply time
- **WHEN** Apply Authority validates
- **THEN** status MUST be `REJECTED` with `CAPABILITY_DRIFT`
- **AND** MUST NOT be classified as `UNAUTHORIZED`

### Requirement: Legacy writer bypass acknowledgment

Until legacy settings writers migrate, architecture MUST acknowledge residual races
with non-Apply mutation paths.

#### Scenario: Legacy bypass race acknowledged (S29)

- **GIVEN** concurrent legacy `AdvSetting` mutation outside Apply Authority
- **WHEN** apply runs with stale `st1` relative to reviewed receipt
- **THEN** Apply MUST reject with `STALE_STATE`
- **AND** global sole write gate for all settings paths MUST NOT be claimed

### Requirement: Stale receipt permanent invalidation

When apply detects `STALE_STATE` relative to reviewed receipt, the receipt MUST
transition to `INVALIDATED` permanently and MUST NOT be reused even if state later
matches the original snapshot.

#### Scenario: Stale receipt invalidates permanently (S30)

- **GIVEN** a dry-run receipt issued for state generation `st1_A`
- **WHEN** apply detects authoritative `st1_B` and returns `STALE_STATE`
- **THEN** receipt MUST become `INVALIDATED`
- **AND** a subsequent return to `st1_A` MUST NOT resurrect the receipt to `ISSUED`

### Requirement: ABA receipt safety

Invalidated receipts MUST NOT become usable again solely because authoritative state
returns to a value that appears identical to the reviewed snapshot (A→B→A).

#### Scenario: ABA does not resurrect receipt (S31)

- **GIVEN** a receipt `INVALIDATED` after `STALE_STATE` at generation B
- **AND** authoritative state later returns to generation A matching the original dry-run token
- **WHEN** a client attempts apply with the old receipt id
- **THEN** status MUST be `REJECTED` with `RECEIPT_INVALID`
- **AND** a fresh dry-run MUST be required

### Requirement: Unauthorized apply does not burn receipt

Authorization failure MUST NOT transition a valid receipt to `INVALIDATED` or `CONSUMED`.

#### Scenario: Unauthorized caller preserves receipt (S32)

- **GIVEN** a valid `ISSUED` receipt and a mismatched unauthorized `ApplyInvocationContext`
- **WHEN** Apply Authority rejects with reason `UNAUTHORIZED`
- **THEN** receipt state MUST remain `ISSUED`
- **AND** no writer MUST be invoked

### Requirement: ChangeSet digest mismatch does not burn receipt

Submitting a wrong `ChangeSet` body against a valid receipt MUST reject the request
without invalidating the receipt that belongs to the originally reviewed ChangeSet.

#### Scenario: Digest mismatch preserves receipt (S33)

- **GIVEN** receipt R bound to `sd1_X` for ChangeSet body X
- **WHEN** apply is called with body Y where `sd1_Y ≠ sd1_X` but the same receipt id
- **THEN** status MUST be `CHANGESET_DIGEST_MISMATCH`
- **AND** receipt R MUST remain `ISSUED` (not `INVALIDATED`)

### Requirement: Commit-unknown blocks blind retry

`UNKNOWN_INTERNAL_COMMIT` MUST block fresh apply on the same receipt until reconciliation
determines committed vs rolled back.

#### Scenario: Commit unknown blocks receipt reuse (S34)

- **GIVEN** an apply attempt ended in `UNKNOWN_INTERNAL_COMMIT`
- **WHEN** a client retries apply with the same receipt without reconciliation
- **THEN** terminal status MUST be `REJECTED` with reason `RECEIPT_BLOCKED_RECONCILIATION`
- **AND** automatic duplicate mutation MUST NOT occur

### Requirement: Authorized idempotent replay without re-execution

Idempotent replay MUST return existing evidence without writer execution or receipt re-consumption.

#### Scenario: Idempotent replay no mutation (S35)

- **GIVEN** a completed `VERIFIED` apply for `(shop_id, idempotency_key)` and fingerprint F
- **AND** an authorized `ApplyInvocationContext`
- **WHEN** apply is invoked again with the same fingerprint F
- **THEN** existing `ApplyEvidenceV1` MUST be returned
- **AND** PG policy writers MUST NOT be invoked again

