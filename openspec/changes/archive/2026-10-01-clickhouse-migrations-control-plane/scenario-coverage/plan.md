# Scenario coverage plan

CHANGE_ID: clickhouse-migrations-control-plane
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: 0390ceb9be3cedd1c9453ab03363d3c679eaec0bab0b3a7970464e3f4d308a33
LIFECYCLE_STATUS: DERIVED
PRODUCT_ACCEPTANCE_REQUIRED: true

This file is derived planning evidence. It states required test evidence.
It does not assert that tests exist, and it is not a coverage PASS.

## GENERATED_FROM

PLAN_EVIDENCE_ID is sha256 of the UTF-8 LF blob below, including the final newline:

```text
clickhouse-migrations-control-plane
plan
design.md:15a0cc2647903e32b1a8662989e7b80ef5a701db3a647db6582b6e0fc8c5f021
specs/clickhouse-migration-lifecycle/spec.md:e8d4fc05d3074a6135037943beafbca0b98338a3824a314d96eaebdfb2291c6b
owner-contract.md:252c243f6bc7813d4c2e3304f43870f9da0e5e85deed0a850ea9b831cbb3e7be
lifecycle:design.md:15a0cc2647903e32b1a8662989e7b80ef5a701db3a647db6582b6e0fc8c5f021
```

INPUTS:

- DESIGN_REVISION: openspec/changes/clickhouse-migrations-control-plane/design.md content_hash 15a0cc2647903e32b1a8662989e7b80ef5a701db3a647db6582b6e0fc8c5f021
- SPEC_REVISION: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md content_hash e8d4fc05d3074a6135037943beafbca0b98338a3824a314d96eaebdfb2291c6b
- LIFECYCLE_REVISION: source design.md Lifecycle section; content_hash of whole design.md 15a0cc2647903e32b1a8662989e7b80ef5a701db3a647db6582b6e0fc8c5f021
- OWNER_CONTRACT_REVISION: openspec/changes/clickhouse-migrations-control-plane/owner-contract.md content_hash 252c243f6bc7813d4c2e3304f43870f9da0e5e85deed0a850ea9b831cbb3e7be

Hashes are sha256 of LF-normalized file bytes.

## LIFECYCLE_COVERAGE

Reviewed owner-contract is present. Lifecycle is taken from design.md
(`LIFECYCLE_STATUS: DERIVED`), checked against that contract. No product
fork is open. `CONFIRM_LIFECYCLE` is not required.

```text
L1 corpus 001-005 already on disk as manual SQL, no target ledger, production set unknown
   COVERED: Register the existing corpus without executing it
   COVERED: Status without a target is not an applied record
L2 accept corpus: id, class, raw SHA-256; do not rewrite SQL; do not execute; 006 stays out
   COVERED: Register the existing corpus without executing it
   COVERED: Qualification stays in the existing SQL
   COVERED: Missing 006 is not imported
   COVERED: Raw bytes no longer match the fingerprint
   COVERED: Unreviewed numeric prefix blocks apply
   COVERED: A semicolon inside a string stops before apply
   COVERED: Test DDL is not canonical
L3 005 is privileged_grant; schema writer does not receive it; this change does not GRANT
   COVERED: Privilege class cannot be substituted
   COVERED: Authorized apply still refuses 005
L4 no sanctioned baseline stays history_unresolved even after ensure-ledger; apply and mark-applied stay blocked; inspect is read-only and does not take the coordinator
   COVERED: File presence is not applied state
   COVERED: Empty ledger does not apply the corpus
   COVERED: Unresolved history blocks apply and mark-applied
   COVERED: Catch-up cannot close unknown history
   COVERED: Inspect does not write and does not baseline
   COVERED: Reconcile without flag or evidence writes nothing
   COVERED: Filename list and undetermined evidence do not apply a version
   COVERED: Missing or zero server UUID fails closed
   COVERED: Plan is dry
   COVERED: Status without a target is not an applied record
L5 isolated config, coordinator DSN, and command sanction open ensure-ledger, reconcile, and apply 001-004 under the session advisory lock; crash leaves partial; no auto-resume; production class refuses
   COVERED: Reconcile requires its own flag and inspection evidence
   COVERED: Schema writer may run only schema DDL under every gate
   COVERED: Statements commit one by one
   COVERED: Same checksum skips SQL
   COVERED: Partial and applying are not idempotent skips
   COVERED: Crash after a successful statement leaves the version unclosed
   COVERED: Apply without authorization refuses
   COVERED: Authorized ensure-ledger holds the advisory lock
   COVERED: Missing coordinator fails closed
   COVERED: Wrong coordinator is not this lock
   COVERED: Lock contention sends no statement
   COVERED: Lock loss stops further SQL
   COVERED: Ledger identity is the server UUID and default_db
   COVERED: Another database is not this corpus target
   COVERED: Ledger checksum differs from the file
   COVERED: Comments are not statements
   COVERED: Honest success and refusal
   COVERED: Isolated apply is real and production is untouched
   COVERED: Production target without a separate GO refuses
   COVERED: Raw bytes no longer match the fingerprint
   COVERED: A semicolon inside a string stops before apply
L6 restart reads the target ledger, not process memory and not PostgreSQL; partial and history_unresolved still forbid a blind run after a new lock acquire
   COVERED: Restart does not continue a partial or unknown history
   COVERED: Ledger checksum differs from the file
L7 this change checks L2-L6 on a substitute isolated target and a substitute coordinator session and does not open production; shop-wide expansion does not start
   COVERED: Isolated apply is real and production is untouched
   COVERED: Production target without a separate GO refuses
   COVERED: The application client is not the migration executor
   COVERED: Alembic stays out of ClickHouse migrations
   COVERED: Shop-wide expansion waits
   COVERED: Test DDL is not canonical
   COVERED: Honest success and refusal
```

LIFECYCLE_GAPS: none
SPEC_SCENARIO_MISSING: none
PLANNING_LIFECYCLE_GAP: none
UNRESOLVED_PRODUCT_SEMANTICS: none

## Steady-state / already-true reconcile

STEADY_STATE_RECONCILE: present

Invariant: once the ledger says `partial` or `history_unresolved`, a later
observe or restart must forbid a blind run. No fresh producer event in WHEN
is required. Creating an empty ledger does not mark `001`–`005` applied.

Already-true scenario:

- Restart does not continue a partial or unknown history

Paired observe and gate scenarios:

- File presence is not applied state
- Unresolved history blocks apply and mark-applied
- Partial and applying are not idempotent skips
- Empty ledger does not apply the corpus
- Crash after a successful statement leaves the version unclosed

## Global evidence rules

RUNNER: `poetry run python -m scripts.clickhouse_migration_control_plane`
Commands: `status`, `validate`, `plan`, `apply`, `inspect`, `reconcile`,
`ensure-ledger`.

SCENARIO_SEAM: call that real runner, or the real in-package function it
uses for corpus acceptance, classification, statement split, and command
gates. Do not reimplement those decisions inside the test.

THIN_ENDS: two substitutes, both in-process. Live network is out of this
change.

- isolated target port: ClickHouse session substitute for ledger create,
  ledger append, schema DDL `001`–`004`, inspect metadata, server UUID, and
  session database.
- coordinator session: PostgreSQL advisory-lock substitute. It records
  acquire, hold, loss, and unlock. It stores no applied status.

Authorized isolated `ensure-ledger`, `reconcile`, and `apply` do mutate the
target port when their own flag, explicit target config, explicit coordinator
DSN, and a held session advisory lock are all present, and when the spec
allows that mutation. `005` still never enters the schema writer.

BOUNDARY_INTEGRATION_WRITE: not_applicable
BOUNDARY_INTEGRATION_READ: not_applicable
LOAD_OR_PERFORMANCE: not_required

Reason: the spec requires substituted ports and forbids a live network call,
production credentials, and a production socket. A live PostgreSQL or
ClickHouse session is not required evidence. Applied state is asserted on
the target-port contract. The coordinator contract asserts lock behavior
only.

SPLIT_WRITE_READ: when a scenario appends and then depends on the later
read, the seam asserts both shapes against one shared contract fixture.
That is the parity proof. It is not a live store test.

BOUNDARY_INTEGRATION_OTHER: `required` means one in-process test of the
shared contract fixture for every thin end that row uses. The scenario seam
and that test consume the same fixture. `not_applicable` means the scenario
never calls a port or the coordinator.

STUB_CONTRACT: `required` when the seam replaces a port or the coordinator.
`not_applicable` when it calls neither.

CONTRACT_ID: isolated-target-port-v1
CONTRACT_ID: coordinator-session-v1

CONTRACT_CASES:

- EXEC_SQL: one schema statement in. Used for authorized `001`–`004`. A call
  that carries `005`, an unreviewed file, drifted SQL, or a comment-only
  statement is a seam failure.
- LEDGER_APPEND: append-only events, including `apply_started`,
  `statement_ok`, `version_applied`, `skipped_already_applied`, and a
  baseline event. Events can carry runner nonce, coordinator lock identity,
  target UUID, database, version, sha256, event type, statement ordinal,
  evidence hash, and timestamp. No in-place update method. PostgreSQL is
  not this ledger.
- LEDGER_READ: events for one server UUID and database `default_db`, ordered
  by `event_seq`. Absence is `ledger_absent`. Visible states include
  `history_unresolved`, `applying`, `partial`, `applied`, `drift`, and
  `blocked_privileged_grant`.
- SERVER_UUID: present and non-zero, missing, or zero. Missing or zero
  refuses. A hostname is not a target id.
- SESSION_DATABASE: `default_db` versus any other database, including
  `test_adv_bot_clickhouse`.
- INSPECT_READ: prepared read-only metadata. No ledger write and no lock.
- ADVISORY_LOCK: `pg_try_advisory_lock` or `pg_advisory_lock` on the
  coordinator substitute; namespace key distinct from the Alembic lock id;
  target key of server UUID plus `default_db`; hold through the mutation;
  false acquire sends no statement; session loss stops the next statement.
  A nonce read is not this acquire.

MOCKING_CONSTRAINTS: the substitutes may stand in for the target port and
the coordinator session. Do not mock corpus parsing, privilege
classification, checksum compare, authorization gates, statement splitting,
command dispatch, or the refusal that happens before a forbidden statement.
A bare `AsyncMock(return_value=True)` is not either contract.

REALITY_CONSTRAINTS: in-process substitutes. Tests may live under
`tests/unit`. Do not require `destructive_local`, a live ClickHouse service,
or a live PostgreSQL service. Forbidden imports and uses: `app.utils.click_house`,
application connection settings, Alembic as the ClickHouse corpus or ledger,
the Alembic lock id as this namespace key, `tests.support.rewrite_default_db_ch_client`,
and test DDL for `test_adv_bot_clickhouse` inside the corpus fingerprint.

EXIT_HONESTY: exit 0 only for intact `validate`, honest `status` (including
unknown history or `ledger_absent`), a `plan` that states its stop reason,
and `ensure-ledger`, `reconcile`, and `apply` when their isolated gates and
held advisory lock succeed. Drift, a substituted `005` class, missing
authorization, unknown history, partial, missing or wrong coordinator, lock
contention or loss, production class, and sending `005` to the schema writer
are non-success.

UNRESOLVED_GAPS: none
OPEN_QUESTIONS: none

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: clickhouse-migrations-control-plane
SOURCE_SPEC_SHA: e8d4fc05d3074a6135037943beafbca0b98338a3824a314d96eaebdfb2291c6b
PLAN_STATUS: ready
SCENARIO_COUNT: 42

Spec path prefix for every SCENARIO_ID:

`openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md`

### SCENARIOS

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Register the existing corpus without executing it
  LIFECYCLE_STEPS: L1, L2
  GIVEN_WHEN_THEN: GIVEN 001-005 exist as manual SQL and no target ledger is attached; WHEN the control plane accepts that corpus; THEN record id, filename, privilege class, and raw-byte SHA-256; do not change SQL bytes; do not execute; do not record any version applied.
  PRODUCTION_ENTRYPOINT: corpus acceptance inside scripts.clickhouse_migration_control_plane, observed through validate
  CAUSAL_PATH: read raw bytes of 001-005; derive class from SQL text; store the fingerprint; stop before the target port and the coordinator
  THIN_ENDS: none
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real corpus acceptance; fingerprint fields present; port execute unused; coordinator unopened
    CONTRACT_CASES: not_applicable
    STUB_CONTRACT: not_applicable
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::File presence is not applied state
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN corpus files are present and 001-004 contain IF NOT EXISTS; WHEN an operator asks whether those versions are applied; THEN do not answer from the files or from IF NOT EXISTS; do not write version_applied for that reason.
  PRODUCTION_ENTRYPOINT: status
  CAUSAL_PATH: status uses ledger or target-not-attached facts only; file presence is not an applied event
  THIN_ENDS: target port LEDGER_READ when a target is attached; LEDGER_APPEND must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real status with files present; no version_applied; answer not taken from IF NOT EXISTS
    CONTRACT_CASES: LEDGER_READ, LEDGER_APPEND
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Raw bytes no longer match the fingerprint
  LIFECYCLE_STEPS: L2, L5
  GIVEN_WHEN_THEN: GIVEN a recorded SHA-256 for 001, 002, 003, 004, or 005; WHEN current raw bytes hash differently; THEN validation reports corpus drift; plan and apply do not execute that SQL; result is non-success.
  PRODUCTION_ENTRYPOINT: validate, then plan and apply
  CAUSAL_PATH: checksum compare fails closed before the schema writer
  THIN_ENDS: EXEC_SQL must not run for the drifted file
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real validate, plan, and apply on drifted bytes; non-success; execute not called
    CONTRACT_CASES: EXEC_SQL
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Ledger checksum differs from the file
  LIFECYCLE_STEPS: L5, L6
  GIVEN_WHEN_THEN: GIVEN a ledger event whose recorded SHA-256 is not the current file checksum; WHEN status, plan, or authorized apply is requested; THEN the version state is drift; apply does not execute the file to force the checksums together; apply is non-success.
  PRODUCTION_ENTRYPOINT: status, plan, apply
  CAUSAL_PATH: ledger read versus raw-byte checksum; apply refuses repair-by-execution even if the advisory lock is held
  THIN_ENDS: LEDGER_READ; EXEC_SQL must not run for that version; coordinator may open on apply and must stop before SQL
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real status, plan, and authorized apply with a ledger checksum that already differs; no repair SQL
    CONTRACT_CASES: LEDGER_READ, EXEC_SQL, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Privilege class cannot be substituted
  LIFECYCLE_STEPS: L3
  GIVEN_WHEN_THEN: GIVEN 005 text is GRANT on system objects; WHEN a fingerprint or caller labels 005 as ordinary schema DDL; THEN validation fails; apply does not execute 005.
  PRODUCTION_ENTRYPOINT: validate, apply
  CAUSAL_PATH: class is derived from SQL text; a contradictory label fails validation before the schema writer
  THIN_ENDS: EXEC_SQL must not receive 005
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real validate and apply with a substituted class label; non-success; 005 text not sent
    CONTRACT_CASES: EXEC_SQL
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Ledger identity is the server UUID and default_db
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN a session whose database is default_db and whose server UUID is present and non-zero; WHEN the control plane reads or writes applied state; THEN it uses default_db.ch_schema_migration_ledger on that server UUID; each state change is a new append; it does not update a row in place; it does not write applied status to PostgreSQL.
  PRODUCTION_ENTRYPOINT: ensure-ledger or authorized apply on an attached isolated target
  CAUSAL_PATH: target identity is server UUID plus default_db; applied state is append-only on the target port; the coordinator stores no applied-status row
  THIN_ENDS: SERVER_UUID, SESSION_DATABASE, LEDGER_APPEND, LEDGER_READ, ADVISORY_LOCK
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real mutating command; identity fields match; append is not an in-place update; coordinator substitute has no applied-status write
    CONTRACT_CASES: SERVER_UUID, SESSION_DATABASE, LEDGER_APPEND, LEDGER_READ, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Missing or zero server UUID fails closed
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN the server UUID cannot be read or is the zero UUID; WHEN the operator attaches that server as the migration target; THEN the system refuses; it does not invent a target id from the hostname.
  PRODUCTION_ENTRYPOINT: status or a mutating command with an attached target
  CAUSAL_PATH: UUID gate refuses before ledger write and before SQL
  THIN_ENDS: SERVER_UUID missing or zero
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real runner; missing UUID and zero UUID each refuse; hostname is not stored as the target id
    CONTRACT_CASES: SERVER_UUID
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Another database is not this corpus target
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN a session whose database is not default_db, including test_adv_bot_clickhouse; WHEN the operator asks to record applied state for 001-005; THEN the system refuses; it does not treat that database as the corpus target.
  PRODUCTION_ENTRYPOINT: apply or ensure-ledger
  CAUSAL_PATH: session database gate refuses before ledger append
  THIN_ENDS: SESSION_DATABASE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real command against a non-default_db session; refusal; no version_applied
    CONTRACT_CASES: SESSION_DATABASE, LEDGER_APPEND
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Empty ledger does not apply the corpus
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN an isolated non-production target whose ledger does not exist yet, with an explicit coordinator DSN and a held session advisory lock; WHEN ensure-ledger runs with its authorization; THEN create only default_db.ch_schema_migration_ledger; leave historic versions unapplied; do not write version_applied for 001-005; do not describe the new ledger as proof that those versions are absent.
  PRODUCTION_ENTRYPOINT: ensure-ledger
  CAUSAL_PATH: advisory lock, then create the ledger only; history stays unresolved; no version_applied
  THIN_ENDS: ADVISORY_LOCK held; ledger create; version_applied append must not run; EXEC_SQL of 001-005 must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real ensure-ledger; ledger created; no version_applied; state is not proven-absent
    CONTRACT_CASES: ADVISORY_LOCK, LEDGER_APPEND, EXEC_SQL
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Status without a target is not an applied record
  LIFECYCLE_STEPS: L1, L4
  GIVEN_WHEN_THEN: GIVEN no target is attached; WHEN the operator requests status; THEN report that the target is not attached; do not record the corpus as applied; do not require a coordinator.
  PRODUCTION_ENTRYPOINT: status
  CAUSAL_PATH: status without a target prints target_not_attached and does not open the port or the coordinator
  THIN_ENDS: none
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real status with no target; target_not_attached; no applied record; coordinator not opened
    CONTRACT_CASES: not_applicable
    STUB_CONTRACT: not_applicable
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Unresolved history blocks apply and mark-applied
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN a target with no sanctioned baseline, even when coordinator config and an apply authorization flag are present; WHEN the operator requests apply or a mark-applied record; THEN refuse; do not execute 001-005; do not write version_applied; apply is non-success.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: history_unresolved or ledger_absent refuses before SQL and before mark-applied, even if the lock can be taken
  THIN_ENDS: LEDGER_READ; EXEC_SQL and version_applied append must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real apply with the authorization flag; non-success; no SQL; no version_applied
    CONTRACT_CASES: LEDGER_READ, EXEC_SQL, LEDGER_APPEND, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Catch-up cannot close unknown history
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN production applied state is unknown; WHEN an operator tries to run 001-005 so the unknown history becomes applied; THEN the catch-up does not run; historic status stays unknown.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: catch-up is the same apply refusal; history is not rewritten
  THIN_ENDS: EXEC_SQL must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real apply of 001-005 while history is unknown; no statements; status remains unknown
    CONTRACT_CASES: EXEC_SQL, LEDGER_READ
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Inspect does not write and does not baseline
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN a readable target and no reconcile authorization; WHEN the operator runs inspect; THEN limit itself to read-only metadata; do not write the ledger; do not acquire the coordinator lock; do not mark any version applied; do not satisfy reconcile.
  PRODUCTION_ENTRYPOINT: inspect
  CAUSAL_PATH: inspect reads prepared metadata only; the coordinator stays closed; reconcile remains a separate command
  THIN_ENDS: INSPECT_READ
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real inspect; no ledger append; no lock acquire; inspect output is not a baseline
    CONTRACT_CASES: INSPECT_READ, LEDGER_APPEND, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Reconcile requires its own flag and inspection evidence
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN an isolated target, inspection evidence, the SHA-256 of that evidence, explicit coordinator config, and a held session advisory lock; WHEN reconcile runs with the baseline authorization flag; THEN append the baseline to the ClickHouse ledger; do not execute 001-005; do not store the baseline in PostgreSQL; do not accept the apply flag as the baseline flag.
  PRODUCTION_ENTRYPOINT: reconcile
  CAUSAL_PATH: own flag, evidence checksum, isolated config, and held lock, then baseline append only
  THIN_ENDS: ADVISORY_LOCK; LEDGER_APPEND of the baseline; EXEC_SQL of 001-005 must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real reconcile with its own flag appends the baseline; apply-flag-only does not; no migration SQL
    CONTRACT_CASES: LEDGER_APPEND, EXEC_SQL, INSPECT_READ, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Filename list and undetermined evidence do not apply a version
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN evidence that is only the names of 001-005, or inspection evidence that leaves a version undetermined; WHEN the operator requests reconcile; THEN a filename list is not evidence; an undetermined version does not receive version_applied.
  PRODUCTION_ENTRYPOINT: reconcile
  CAUSAL_PATH: evidence shape gate before a baseline append
  THIN_ENDS: LEDGER_APPEND of version_applied must not run for a filename list or an undetermined version
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real reconcile; filename list refused; undetermined version not applied
    CONTRACT_CASES: LEDGER_APPEND, INSPECT_READ
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Reconcile without flag or evidence writes nothing
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN no baseline authorization flag, or no evidence checksum, or no coordinator config; WHEN the operator requests reconcile; THEN the system does not write a baseline.
  PRODUCTION_ENTRYPOINT: reconcile
  CAUSAL_PATH: missing authority refuses before ledger append
  THIN_ENDS: LEDGER_APPEND must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real reconcile for each missing input; no baseline write
    CONTRACT_CASES: LEDGER_APPEND, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Plan is dry
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN a corpus and a target that is missing, unresolved, privileged, drifted, partial, or production; WHEN the operator requests a plan; THEN report version order, privilege class, checksum, statements, and the stop reason; do not execute SQL; do not write the ledger; do not acquire a coordinator lock.
  PRODUCTION_ENTRYPOINT: plan
  CAUSAL_PATH: dry plan; coordinator stays closed
  THIN_ENDS: EXEC_SQL, LEDGER_APPEND, and ADVISORY_LOCK must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real plan; stop reason present; no execute; no lock acquire
    CONTRACT_CASES: EXEC_SQL, ADVISORY_LOCK, LEDGER_APPEND
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Apply without authorization refuses
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN an isolated target whose history is already baselined and a schema version eligible under every other gate; WHEN apply is requested without the apply authorization flag; THEN refuse before any statement; do not execute SQL; result is non-success.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: missing apply flag stops before mutation
  THIN_ENDS: EXEC_SQL and LEDGER_APPEND must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real apply without the flag; non-success; no statement
    CONTRACT_CASES: EXEC_SQL, LEDGER_APPEND
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Schema writer may run only schema DDL under every gate
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN an isolated non-production target, explicit target config, explicit coordinator config, a held advisory lock for that server UUID and default_db, a sanctioned baseline, a matching checksum, and version 001, 002, 003, or 004 that is not partial; WHEN apply runs with the apply authorization flag; THEN execute that version's schema DDL; append apply_started, then statement_ok for each ordinal, then version_applied only after every statement succeeds; record runner nonce, lock identity, target UUID, database, version, sha256, event, ordinal, and timestamp; do not execute 005.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: every gate holds, then the schema writer sends 001-004 only
  THIN_ENDS: ADVISORY_LOCK held; EXEC_SQL of schema DDL; LEDGER_APPEND of apply_started, statement_ok, and version_applied
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real authorized apply; SQL sent; event order holds; 005 text absent from the writer
    CONTRACT_CASES: EXEC_SQL, LEDGER_APPEND, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Honest success and refusal
  LIFECYCLE_STEPS: L5, L7
  GIVEN_WHEN_THEN: GIVEN a command among status, validate, plan, ensure-ledger, reconcile, and apply; WHEN the command finishes; THEN status may succeed while history is unknown; validate succeeds only when the corpus is intact; plan may succeed with a plan that stops; ensure-ledger, reconcile, and apply succeed only when their isolated gates and held advisory lock succeed; drift, a substituted 005 class, missing authorization, unknown history, partial, missing coordinator, lock contention, and sending 005 to the schema writer are non-success.
  PRODUCTION_ENTRYPOINT: status, validate, plan, ensure-ledger, reconcile, apply
  CAUSAL_PATH: exit 0 only for the honest success cases; mutating success uses both substitutes; refusals stop before the forbidden mutation
  THIN_ENDS: mutating success uses the target port and the coordinator session; refusals send no forbidden statement
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real commands; exit codes match allowed success and the named refusals; no production socket
    CONTRACT_CASES: EXEC_SQL, LEDGER_APPEND, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Authorized apply still refuses 005
  LIFECYCLE_STEPS: L3
  GIVEN_WHEN_THEN: GIVEN 005 is in the corpus as a privileged grant, the target is isolated, the coordinator lock is held, and the apply authorization flag is set; WHEN apply reaches 005; THEN refuse with blocked_privileged_grant before calling the schema writer; the writer does not receive the 005 text; 005 is not executed; result is non-success.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: privilege gate before the schema writer is called
  THIN_ENDS: EXEC_SQL must not receive 005; ADVISORY_LOCK may already be held
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real apply reaches 005 and refuses; writer payload has no 005 text
    CONTRACT_CASES: EXEC_SQL, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Qualification stays in the existing SQL
  LIFECYCLE_STEPS: L2
  GIVEN_WHEN_THEN: GIVEN the existing bytes of 001-005; WHEN the corpus is validated; THEN 001-004 still name default_db objects; 005 still names system objects in the GRANT; the files are not rewritten.
  PRODUCTION_ENTRYPOINT: validate
  CAUSAL_PATH: byte and qualification check; no rewrite
  THIN_ENDS: none
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real validate; qualification strings remain; raw bytes unchanged
    CONTRACT_CASES: not_applicable
    STUB_CONTRACT: not_applicable
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Missing 006 is not imported
  LIFECYCLE_STEPS: L2
  GIVEN_WHEN_THEN: GIVEN 006 is absent from this database and exists only in another uncommitted worktree; WHEN the control plane builds the corpus fingerprint; THEN the fingerprint is exactly 001-005; that other 006 is not copied or read; absence of 006 does not itself mark the corpus drifted.
  PRODUCTION_ENTRYPOINT: validate
  CAUSAL_PATH: fingerprint set is closed at 001-005
  THIN_ENDS: none
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real fingerprint; ids are 001-005 only; no foreign 006 read
    CONTRACT_CASES: not_applicable
    STUB_CONTRACT: not_applicable
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Unreviewed numeric prefix blocks apply
  LIFECYCLE_STEPS: L2
  GIVEN_WHEN_THEN: GIVEN a SQL file whose numeric prefix is not in the fingerprint, including an unreviewed 006 placed where the corpus is read; WHEN the operator requests apply; THEN classify that file as an unreviewed version; block apply; do not execute it.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: unreviewed-version gate before SQL
  THIN_ENDS: EXEC_SQL must not run for that file
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real apply; non-success; unreviewed file not sent
    CONTRACT_CASES: EXEC_SQL
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Same checksum skips SQL
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN a schema version whose latest ledger event is version_applied for the current raw-byte SHA-256, and the coordinator lock is held; WHEN authorized apply runs again on the isolated target; THEN do not send the SQL again; leave the version applied.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: idempotent skip under the held lock; skipped_already_applied may be appended; SQL is not repeated
  THIN_ENDS: ADVISORY_LOCK held; EXEC_SQL must not run; LEDGER_APPEND only the optional skip audit
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real second apply; SQL not sent; version remains applied
    CONTRACT_CASES: EXEC_SQL, LEDGER_READ, LEDGER_APPEND, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Partial and applying are not idempotent skips
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN a version whose latest state is partial or applying; WHEN apply runs again, including with a new apply authorization and a newly acquired advisory lock; THEN fail closed; do not skip it as already applied; do not replay its statements; do not resume from the middle; IF NOT EXISTS does not mark it complete.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: partial or applying gate after lock acquire
  THIN_ENDS: ADVISORY_LOCK may be held; EXEC_SQL must not run; version_applied must not be appended
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real re-apply for partial and for applying; non-success; no replay; no version_applied
    CONTRACT_CASES: LEDGER_READ, EXEC_SQL, LEDGER_APPEND, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Statements commit one by one
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN an authorized apply of schema version 001, 002, or 004 on an isolated target whose history is baselined, whose checksum matches, and whose coordinator session holds the advisory lock; WHEN apply runs; THEN append apply_started before statements; append statement_ok with that statement's ordinal after each success; append version_applied only after every statement succeeds; do not claim the file was one transaction.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: one-statement step boundary on the target port under the held coordinator session
  THIN_ENDS: EXEC_SQL one statement at a time; LEDGER_APPEND in that order; ADVISORY_LOCK held across them
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real apply; event order and ordinals; no single-transaction claim
    CONTRACT_CASES: EXEC_SQL, LEDGER_APPEND, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::A semicolon inside a string stops before apply
  LIFECYCLE_STEPS: L2, L5
  GIVEN_WHEN_THEN: GIVEN a file whose statement parse sees a semicolon inside a string literal; WHEN the operator validates the corpus; THEN validation fails; apply does not start.
  PRODUCTION_ENTRYPOINT: validate, then apply
  CAUSAL_PATH: statement splitter fails closed before any target statement
  THIN_ENDS: EXEC_SQL must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real validate fails; real apply does not send SQL
    CONTRACT_CASES: EXEC_SQL
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Comments are not statements
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN a full-line comment, including a comment about recreating an object; WHEN apply splits a version into statements; THEN that comment is not sent as SQL; the system does not recreate objects because of the comment.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: full-line comments are removed before the step boundary
  THIN_ENDS: EXEC_SQL payloads contain no comment-only statement
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real split on authorized apply; comment absent from sent SQL; no recreate caused by the comment
    CONTRACT_CASES: EXEC_SQL
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Crash after a successful statement leaves the version unclosed
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN apply_started is recorded and at least one statement has succeeded; WHEN the process or the coordinator session stops before version_applied; THEN the version remains partial or applying; already successful statements remain; no rollback; the next statement is not sent; apply of that version and of following versions stops.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: gap between statement_ok and version_applied fails closed
  THIN_ENDS: EXEC_SQL stops; no version_applied append; coordinator session ends
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real apply interrupted after one success; no next statement; no version_applied; no rollback
    CONTRACT_CASES: EXEC_SQL, LEDGER_APPEND, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Restart does not continue a partial or unknown history
  LIFECYCLE_STEPS: L6
  GIVEN_WHEN_THEN: GIVEN the ledger already says partial or history_unresolved, with no fresh producer event in this process; WHEN a new process starts, acquires the advisory lock, and reads the target; THEN take that state from the ClickHouse ledger; do not continue a blind run from memory; do not read applied status from PostgreSQL; do not resume the partial file from the middle.
  PRODUCTION_ENTRYPOINT: apply after process restart
  CAUSAL_PATH: ledger read is authority; a new lock acquire does not authorize resume
  THIN_ENDS: LEDGER_READ; ADVISORY_LOCK held; EXEC_SQL must not resume the file
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: new process for partial and for history_unresolved; no resume; PostgreSQL substitute is not the status source
    CONTRACT_CASES: LEDGER_READ, EXEC_SQL, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Authorized ensure-ledger holds the advisory lock
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN an isolated target, an explicit coordinator DSN, and the ensure-ledger authorization; WHEN ensure-ledger runs; THEN acquire the session advisory lock for that server UUID and default_db before creating the ledger; keep the session until creation is terminal or has failed; do not mark 001-005 applied.
  PRODUCTION_ENTRYPOINT: ensure-ledger
  CAUSAL_PATH: lock before the first target statement; the session spans ledger creation
  THIN_ENDS: ADVISORY_LOCK then ledger create
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real ensure-ledger; lock key is the migration-control namespace plus that target; no version_applied
    CONTRACT_CASES: ADVISORY_LOCK, LEDGER_APPEND
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Missing coordinator fails closed
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN an isolated target and a mutating authorization flag; WHEN ensure-ledger, reconcile, or apply is requested without an explicit coordinator DSN; THEN refuse with blocked_missing_coordinator before any target statement; do not open the application database connection as a substitute.
  PRODUCTION_ENTRYPOINT: ensure-ledger, reconcile, apply
  CAUSAL_PATH: missing DSN before lock acquire and before SQL
  THIN_ENDS: no target statement; application database is not opened
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: each mutating command refuses; no statement; application database substitute is unused
    CONTRACT_CASES: ADVISORY_LOCK, EXEC_SQL
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Wrong coordinator is not this lock
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN a runner that would take the Alembic advisory lock, call app.db.migrate, or silently use application DATABASE_URL, Redis, a file lock, or a ClickHouse nonce; WHEN a mutating command starts; THEN refuse before any target statement; that other mechanism is not the migration-control lock.
  PRODUCTION_ENTRYPOINT: ensure-ledger, reconcile, or apply
  CAUSAL_PATH: coordinator identity gate before the first target statement
  THIN_ENDS: no target statement
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real mutating command refuses those substitutes; Alembic lock id is not the namespace key
    CONTRACT_CASES: ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Lock contention sends no statement
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN two runner instances for the same server UUID and default_db configured with the same coordinator; WHEN the second try-lock returns false; THEN that instance refuses with blocked_lock_contention; it sends no target statement; a nonce read is not exclusive acquisition.
  PRODUCTION_ENTRYPOINT: apply or ensure-ledger
  CAUSAL_PATH: try-lock false stops before SQL
  THIN_ENDS: ADVISORY_LOCK returns false; EXEC_SQL must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: second instance; no statement; nonce read does not authorize SQL
    CONTRACT_CASES: ADVISORY_LOCK, EXEC_SQL
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Lock loss stops further SQL
  LIFECYCLE_STEPS: L5
  GIVEN_WHEN_THEN: GIVEN a runner whose coordinator session dies after apply_started or after a statement_ok; WHEN the next statement would be sent; THEN do not send that statement; leave the version applying or partial; do not roll back a statement that already succeeded.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: liveness check before each subsequent statement
  THIN_ENDS: ADVISORY_LOCK lost; next EXEC_SQL must not run
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real apply; session drop; no next statement; no rollback
    CONTRACT_CASES: ADVISORY_LOCK, EXEC_SQL, LEDGER_APPEND
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Isolated apply is real and production is untouched
  LIFECYCLE_STEPS: L5, L7
  GIVEN_WHEN_THEN: GIVEN an isolated executor with a substituted target port, a substituted coordinator session, no production credentials, and no production socket; WHEN tests exercise authorized apply of schema DDL 001-004 after a baseline and under the held advisory lock; THEN execute that schema DDL and append version_applied only after all statements succeed; do not open a production connection; do not perform a live network call.
  PRODUCTION_ENTRYPOINT: apply
  CAUSAL_PATH: isolated substitutes only; production socket stays closed
  THIN_ENDS: target port and coordinator session; production socket absent
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real authorized apply on the substitutes; version_applied after success; no production client and no live socket
    CONTRACT_CASES: EXEC_SQL, LEDGER_APPEND, ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Production target without a separate GO refuses
  LIFECYCLE_STEPS: L5, L7
  GIVEN_WHEN_THEN: GIVEN a target whose class is production, even with coordinator config and an apply authorization flag; WHEN ensure-ledger, reconcile, or apply is requested; THEN refuse with blocked_production_target before any statement; this change is not the future operator GO.
  PRODUCTION_ENTRYPOINT: ensure-ledger, reconcile, apply
  CAUSAL_PATH: production class refuses before lock acquire and before SQL
  THIN_ENDS: no target statement
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: each mutating command refuses before a statement
    CONTRACT_CASES: ADVISORY_LOCK, EXEC_SQL
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::The application client is not the migration executor
  LIFECYCLE_STEPS: L7
  GIVEN_WHEN_THEN: GIVEN the application ClickHouse client and its connection settings; WHEN the migration control plane is built and tested; THEN it does not use that client; it does not read those settings; it does not take production credentials from them.
  PRODUCTION_ENTRYPOINT: package import of scripts.clickhouse_migration_control_plane
  CAUSAL_PATH: runner module graph excludes the application ClickHouse client
  THIN_ENDS: none
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: build check; forbidden client module and application connection settings are unused
    CONTRACT_CASES: not_applicable
    STUB_CONTRACT: not_applicable
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Alembic stays out of ClickHouse migrations
  LIFECYCLE_STEPS: L7
  GIVEN_WHEN_THEN: GIVEN the existing PostgreSQL Alembic history and its advisory lock; WHEN the ClickHouse corpus, ledger, and coordinator are defined; THEN Alembic does not own ClickHouse versions; it does not store the ledger; it does not contain 001-005 as its revisions; its lock id is not the migration-control namespace key.
  PRODUCTION_ENTRYPOINT: validate and the lock key of a mutating command
  CAUSAL_PATH: separate corpus package and a distinct coordinator namespace key
  THIN_ENDS: ADVISORY_LOCK key is not the Alembic lock id
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: fingerprint is not stored as Alembic revisions; lock key differs from the Alembic id
    CONTRACT_CASES: ADVISORY_LOCK
    STUB_CONTRACT: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Test DDL is not canonical
  LIFECYCLE_STEPS: L2, L7
  GIVEN_WHEN_THEN: GIVEN session DDL that creates objects in test_adv_bot_clickhouse and a test seam that rewrites default_db names; WHEN the corpus fingerprint is built; THEN that test DDL is not part of the fingerprint; the control plane does not use that rewrite seam; 001-004 still name default_db.
  PRODUCTION_ENTRYPOINT: validate
  CAUSAL_PATH: corpus reader ignores test DDL and the rewrite seam
  THIN_ENDS: none
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: real fingerprint; test-database objects absent; rewrite seam unused; default_db names remain
    CONTRACT_CASES: not_applicable
    STUB_CONTRACT: not_applicable
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global

- SCENARIO_ID: openspec/changes/clickhouse-migrations-control-plane/specs/clickhouse-migration-lifecycle/spec.md::Shop-wide expansion waits
  LIFECYCLE_STEPS: L7
  GIVEN_WHEN_THEN: GIVEN this migration lifecycle is the change under test; WHEN readiness of the change is judged; THEN shop-wide campaign data collection does not start as part of this change; readiness does not depend on a production migration, secrets, Kubernetes, or deployment.
  PRODUCTION_ENTRYPOINT: readiness path of this change
  CAUSAL_PATH: readiness does not invoke shop-wide collection
  THIN_ENDS: none
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: readiness path does not start shop-wide collection and does not require production, secrets, Kubernetes, or deployment
    CONTRACT_CASES: not_applicable
    STUB_CONTRACT: not_applicable
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    LOAD_OR_PERFORMANCE: not_required
  REALITY_CONSTRAINTS: global
  MOCKING_CONSTRAINTS: global
