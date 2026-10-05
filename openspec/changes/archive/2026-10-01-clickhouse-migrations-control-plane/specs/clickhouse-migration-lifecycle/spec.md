## ADDED Requirements

### Requirement: Corpus identity stays immutable and separate from applied state

The system MUST treat the canonical ClickHouse migration corpus of this
database as exactly the existing versions `001`, `002`, `003`, `004`, and
`005`, and MUST treat corpus identity as a different fact from applied state
on a target. Identity is the version id, the existing filename, the privilege
class derived from the SQL text, and the SHA-256 of the raw file bytes with
no newline normalization and no comment stripping. The system MUST NOT
rewrite the bytes of `001`–`005`. Accepting a file into the corpus MUST NOT
execute its SQL. Presence of a file, and `IF NOT EXISTS` inside `001`–`004`,
MUST NOT be a record that the version was applied. The system MUST NOT store
applied state as a file in git or as a PostgreSQL row.

#### Scenario: Register the existing corpus without executing it

- **GIVEN** versions `001` through `005` already exist as manual SQL and no
  target ledger is attached
- **WHEN** the control plane accepts that corpus
- **THEN** it MUST record each version id, filename, privilege class, and
  raw-byte SHA-256
- **AND** MUST NOT change the SQL bytes
- **AND** MUST NOT execute any statement
- **AND** MUST NOT record any version as applied

#### Scenario: File presence is not applied state

- **GIVEN** the corpus files are present and `001`–`004` contain
  `IF NOT EXISTS`
- **WHEN** an operator asks whether those versions are applied on a target
- **THEN** the system MUST NOT answer from the files or from `IF NOT EXISTS`
- **AND** MUST NOT write a `version_applied` event for that reason

### Requirement: Checksum mismatch is drift and blocks execution

The system MUST refuse to execute SQL when the corpus fingerprint is
missing, unreadable, or not the SHA-256 of the current raw file bytes.
The system MUST also treat a ledger checksum that differs from the current
file checksum as drift. Drift MUST NOT be repaired by rewriting `001`–`005`
or by running the file. A recorded privilege class that contradicts the SQL
text, including a record that calls `005` ordinary schema DDL, MUST be
drift and MUST fail validation.

#### Scenario: Raw bytes no longer match the fingerprint

- **GIVEN** a recorded SHA-256 for version `001`, `002`, `003`, `004`, or
  `005`
- **WHEN** the current raw bytes of that file hash to a different value
- **THEN** validation MUST report corpus drift
- **AND** plan and apply MUST NOT execute that SQL
- **AND** the command result MUST be non-success

#### Scenario: Ledger checksum differs from the file

- **GIVEN** a target ledger event for a version whose recorded SHA-256 is
  not the current file checksum
- **WHEN** the operator requests status, a plan, or authorized apply
- **THEN** the version state MUST be drift
- **AND** apply MUST NOT execute the file to force the checksums back
  together
- **AND** the apply result MUST be non-success

#### Scenario: Privilege class cannot be substituted

- **GIVEN** `005` text is `GRANT` on `system` objects
- **WHEN** a fingerprint or caller labels `005` as ordinary schema DDL
- **THEN** validation MUST fail
- **AND** apply MUST NOT execute `005`

### Requirement: Applied state is an append-only ledger bound to one server and database

Applied state for this corpus MUST live only in an append-only ledger on
the ClickHouse being migrated:
`default_db.ch_schema_migration_ledger`. The target id MUST be that
server's own server UUID. If the server UUID is unavailable or zero, the
system MUST stop and MUST NOT substitute a hostname or any other name.
The session database MUST be `default_db`. Any other database, including
`test_adv_bot_clickhouse`, MUST NOT be a target of this corpus. Current
version state MUST be the ledger event with the greatest sequence for that
target and version, not a row mutated in place, not process memory, and not
a PostgreSQL row. The system MUST NOT use a PostgreSQL table, an Alembic
revision, or Redis as this ledger. PostgreSQL MUST store no applied status.
Ledger events MUST be able to record `runner_nonce`, coordinator lock
identity, target UUID, database, version, sha256, event type, statement
ordinal, evidence hash, and timestamp. Creating the ledger MUST NOT mark
`001`–`005` applied. Absence of the ledger MUST remain `ledger_absent`
until `ensure-ledger` creates it. After creation without a baseline the
state MUST be `history_unresolved`. The operator-visible states MUST be
`ledger_absent`, `history_unresolved`, `applying`, `partial`, `applied`,
`drift`, and `blocked_privileged_grant`. `history_unresolved` MUST mean
"not established". It MUST NOT mean "proven absent on the server".

#### Scenario: Ledger identity is the server UUID and default_db

- **GIVEN** a session whose database is `default_db` and whose server UUID
  is present and non-zero
- **WHEN** the control plane reads or writes applied state
- **THEN** it MUST use `default_db.ch_schema_migration_ledger` on that
  server UUID
- **AND** each state change MUST be a new append
- **AND** MUST NOT update a ledger row in place
- **AND** MUST NOT write that applied status to PostgreSQL

#### Scenario: Missing or zero server UUID fails closed

- **GIVEN** the server UUID cannot be read or is the zero UUID
- **WHEN** the operator attaches that server as the migration target
- **THEN** the system MUST refuse
- **AND** MUST NOT invent a target id from the hostname

#### Scenario: Another database is not this corpus target

- **GIVEN** a session whose database is not `default_db`, including
  `test_adv_bot_clickhouse`
- **WHEN** the operator asks to record applied state for `001`–`005`
- **THEN** the system MUST refuse
- **AND** MUST NOT treat that database as the corpus target

#### Scenario: Empty ledger does not apply the corpus

- **GIVEN** an isolated non-production target whose ledger tables do not
  yet exist, with an explicit coordinator DSN and a held session advisory
  lock
- **WHEN** the operator ensures the ledger with the ensure-ledger
  authorization
- **THEN** the system MUST create only `default_db.ch_schema_migration_ledger`
- **AND** MUST leave historic versions unapplied
- **AND** MUST NOT write `version_applied` for `001`–`005`
- **AND** MUST NOT describe the new ledger as proof that those versions
  are absent on the server

#### Scenario: Status without a target is not an applied record

- **GIVEN** no target is attached
- **WHEN** the operator requests status
- **THEN** the system MUST report that the target is not attached
- **AND** MUST NOT record the corpus as applied
- **AND** MUST NOT require a coordinator

### Requirement: Unknown historic state fails closed

Until a separately authorized baseline exists, historic applied state on
production MUST remain explicitly unknown. While the target is
`ledger_absent` or `history_unresolved`, apply MUST refuse, marking a
version applied MUST refuse, and a catch-up run of `001`–`005` MUST NOT
run. The system MUST NOT close that unknown history by rewriting `001`–`005`.
A manual client invocation, a runtime truncate of system logs, and test
DDL MUST NOT become the baseline record.

#### Scenario: Unresolved history blocks apply and mark-applied

- **GIVEN** a target with no sanctioned baseline, even when coordinator
  config and an apply authorization flag are present
- **WHEN** the operator requests apply or a mark-applied record
- **THEN** the system MUST refuse
- **AND** MUST NOT execute `001`–`005`
- **AND** MUST NOT write `version_applied`
- **AND** the apply result MUST be non-success

#### Scenario: Catch-up cannot close unknown history

- **GIVEN** production applied state is unknown
- **WHEN** an operator tries to run `001`–`005` so the unknown history
  becomes applied
- **THEN** the system MUST NOT run that catch-up
- **AND** MUST leave the historic status unknown

### Requirement: Inspect and reconcile are different authorities

Read-only inspect and baseline reconcile MUST have separate authority and
MUST NOT replace each other. Inspect MUST only read target metadata and
MUST NOT write the ledger and MUST NOT acquire the coordinator lock.
Reconcile MUST append a baseline only when its own authorization flag, the
SHA-256 of inspection evidence, explicit isolated target config, and a held
PostgreSQL advisory lock are all present. That flag MUST stay distinct from
the apply authorization flag. The evidence MUST be an inspection result. A
list of corpus filenames MUST NOT be evidence. A version left undetermined
in the evidence MUST NOT receive `version_applied`. Reconcile MUST NOT
execute SQL of `001`–`005`. Status, validate, plan, and inspect MUST NOT
acquire a writer lock and MUST NOT write the ledger.

#### Scenario: Inspect does not write and does not baseline

- **GIVEN** a readable target and no reconcile authorization
- **WHEN** the operator runs inspect
- **THEN** the system MUST limit itself to read-only metadata
- **AND** MUST NOT write the ledger
- **AND** MUST NOT acquire the coordinator lock
- **AND** MUST NOT mark any version applied
- **AND** MUST NOT satisfy reconcile

#### Scenario: Reconcile requires its own flag and inspection evidence

- **GIVEN** an isolated target, inspection evidence, the SHA-256 of that
  evidence, explicit coordinator config, and a held session advisory lock
- **WHEN** the operator runs reconcile with the baseline authorization flag
- **THEN** the system MUST append the baseline to the ClickHouse ledger
- **AND** MUST NOT execute `001`–`005`
- **AND** MUST NOT store the baseline in PostgreSQL
- **AND** MUST NOT accept the apply flag as the baseline flag

#### Scenario: Filename list and undetermined evidence do not apply a version

- **GIVEN** evidence that is only the names of `001`–`005`, or inspection
  evidence that leaves a version undetermined
- **WHEN** the operator requests reconcile
- **THEN** a filename list MUST NOT be accepted as evidence
- **AND** an undetermined version MUST NOT receive `version_applied`

#### Scenario: Reconcile without flag or evidence writes nothing

- **GIVEN** no baseline authorization flag, or no evidence checksum, or no
  coordinator config
- **WHEN** the operator requests reconcile
- **THEN** the system MUST NOT write a baseline

### Requirement: Plan does not execute and apply needs explicit authorization

The system MUST provide status, corpus validation, drift detection, and a
plan that does not execute SQL, together with checksum integrity and an
audit of refusal. Plan MUST show the dry statement order and the stop
reason, including no target, missing coordinator, unknown history, `005`,
drift, partial, or production class, and MUST NOT execute SQL and MUST NOT
acquire a lock. Apply without the apply authorization flag, without
explicit target config, or without explicit coordinator config MUST refuse
before any target mutation. The schema writer MUST execute schema DDL for
`001`–`004` only when the target class is isolated, history is baselined,
the checksum matches, the version is not `partial` or `applying`, the apply
flag is set, and the session advisory lock is held. Apply of a production
target MUST refuse. Validation MUST succeed only for an intact corpus.
Status MUST be allowed to succeed while reporting unknown history. Plan
MUST be allowed to succeed by producing a plan. A completed authorized
isolated apply MUST be allowed to succeed. Corpus drift, a substituted
class for `005`, missing authorization, unknown history, partial, missing
or wrong coordinator, lock contention or loss, production class, and an
attempt to send `005` through the schema writer MUST be non-success.

#### Scenario: Plan is dry

- **GIVEN** a corpus and a target that is missing, unresolved, privileged,
  drifted, partial, or production
- **WHEN** the operator requests a plan
- **THEN** the system MUST report version order, privilege class, checksum,
  statements, and the stop reason
- **AND** MUST NOT execute SQL
- **AND** MUST NOT write the ledger
- **AND** MUST NOT acquire a coordinator lock

#### Scenario: Apply without authorization refuses

- **GIVEN** an isolated target whose history is already baselined and a
  schema version eligible under every other gate
- **WHEN** the operator requests apply without the apply authorization flag
- **THEN** the system MUST refuse before any statement
- **AND** MUST NOT execute SQL
- **AND** the result MUST be non-success

#### Scenario: Schema writer may run only schema DDL under every gate

- **GIVEN** an isolated non-production target, explicit target config,
  explicit coordinator config, a held PostgreSQL advisory lock for that
  server UUID and `default_db`, a sanctioned baseline, a matching checksum,
  and version `001`, `002`, `003`, or `004` that is not `partial`
- **WHEN** the operator runs apply with the apply authorization flag
- **THEN** the schema writer MUST execute that version's schema DDL
- **AND** MUST append `apply_started`, then `statement_ok` for each
  ordinal, then `version_applied` only after every statement succeeds
- **AND** MUST record runner nonce, coordinator lock identity, target UUID,
  database, version, sha256, event, ordinal, and timestamp on those events
- **AND** MUST NOT execute `005`

#### Scenario: Honest success and refusal

- **GIVEN** a command among status, validate, plan, ensure-ledger,
  reconcile, and apply
- **WHEN** the command finishes
- **THEN** status MUST be allowed to succeed while the history is unknown
- **AND** validate MUST succeed only when the corpus is intact
- **AND** plan MUST be allowed to succeed with a plan that stops
- **AND** ensure-ledger, reconcile, and apply MUST be allowed to succeed
  only when their isolated gates and held advisory lock succeed
- **AND** drift, a substituted `005` class, missing authorization, unknown
  history, partial, missing coordinator, lock contention, and sending `005`
  to the schema writer MUST be non-success

### Requirement: Privileged grant 005 never enters the schema writer

`005` MUST remain a privileged `GRANT`. Planning classifies it from the
SQL text; that classification is not an Owner decision. The schema writer
MUST NOT receive the text of `005` and MUST NOT execute it. This change
MUST NOT create a privileged-grant writer and MUST NOT execute `005`.
Apply of `005` MUST refuse with `blocked_privileged_grant` before the
schema writer is called. Accepting `005` into the corpus MUST NOT include
executing it. The text of `005` MUST keep its `system` object
qualification. The text of `001`–`004` MUST keep `default_db` object
qualification.

#### Scenario: Authorized apply still refuses 005

- **GIVEN** `005` is in the corpus as a privileged grant, the target is
  isolated, the coordinator lock is held, and the operator sets the apply
  authorization flag
- **WHEN** apply reaches `005`
- **THEN** the system MUST refuse with `blocked_privileged_grant` before
  calling the schema writer
- **AND** the schema writer MUST NOT receive the `005` text
- **AND** `005` MUST NOT be executed
- **AND** the result MUST be non-success

#### Scenario: Qualification stays in the existing SQL

- **GIVEN** the existing bytes of `001`–`005`
- **WHEN** the corpus is validated
- **THEN** `001`–`004` MUST still name `default_db` objects
- **AND** `005` MUST still name `system` objects in the `GRANT`
- **AND** the system MUST NOT rewrite those files

### Requirement: Missing 006 stays out and an unreviewed version blocks apply

This database has no version `006`. The system MUST NOT copy `006` and
MUST NOT modify `006`. The fingerprint of this change MUST NOT contain
`006`. Absence of `006` MUST NOT by itself block the canonical corpus.
The protocol MUST leave room for a later reviewed version to enter in a
separate change. A file whose numeric prefix is not in this fingerprint
MUST be an unreviewed version and MUST block apply. The system MUST NOT
read a `006` file from another worktree in order to build this corpus.

#### Scenario: Missing 006 is not imported

- **GIVEN** `006` is absent from this database and exists only in another
  uncommitted worktree
- **WHEN** the control plane builds the corpus fingerprint
- **THEN** the fingerprint MUST be exactly `001`–`005`
- **AND** MUST NOT copy or read that other `006`
- **AND** absence of `006` MUST NOT itself mark the corpus drifted

#### Scenario: Unreviewed numeric prefix blocks apply

- **GIVEN** a SQL file with a numeric prefix that is not in the fingerprint,
  including an unreviewed `006` placed where the corpus is read
- **WHEN** the operator requests apply
- **THEN** the system MUST classify that file as an unreviewed version
- **AND** MUST block apply
- **AND** MUST NOT execute it

### Requirement: Replaying a closed version is idempotent

A repeated apply of a version already `applied` with the same SHA-256 MUST
NOT execute its SQL again. Under a held coordinator lock the system MAY
append `skipped_already_applied`. Versions in `partial` or `applying` MUST
NOT be skipped as applied and MUST NOT be replayed. A later run while the
latest state is `partial` or `applying` MUST fail until an explicit operator
reconciliation policy exists. This change MUST NOT define that resume
policy. Success of a statement that uses `IF NOT EXISTS` MUST NOT by itself
write `version_applied`.

#### Scenario: Same checksum skips SQL

- **GIVEN** a schema version whose latest ledger event is `version_applied`
  for the current raw-byte SHA-256, and the coordinator lock is held
- **WHEN** the operator runs authorized apply again on the isolated target
- **THEN** the system MUST NOT send the SQL again
- **AND** MUST leave the version applied

#### Scenario: Partial and applying are not idempotent skips

- **GIVEN** a version whose latest state is `partial` or `applying`
- **WHEN** the operator runs apply again, including with a new apply
  authorization and a newly acquired advisory lock
- **THEN** the system MUST fail closed
- **AND** MUST NOT skip it as already applied
- **AND** MUST NOT replay its statements
- **AND** MUST NOT resume from the middle of the file
- **AND** MUST NOT mark it complete because a statement uses `IF NOT EXISTS`

### Requirement: A multi-statement file is not a transaction

Versions `001`, `002`, `004`, and `005` contain more than one statement.
Version `003` is a single `ALTER`. The system MUST treat the file as
non-atomic. The step boundary MUST be one statement after removal of
full-line `--` comments. Comments MUST NOT be executed, and a comment that
mentions recreating an object MUST NOT cause the system to recreate it.
If parsing finds a semicolon inside a string literal, validation MUST fail
and apply MUST NOT start. On an authorized isolated apply the system MUST
append `apply_started` before statements, `statement_ok` with the ordinal
after each success, and `version_applied` only after all statements
succeed. The system MUST NOT treat the file as a transaction and MUST NOT
promise automatic rollback of a statement that already succeeded.

#### Scenario: Statements commit one by one

- **GIVEN** an authorized apply of schema version `001`, `002`, or `004`
  on an isolated target whose history is baselined, whose checksum matches,
  and whose coordinator session holds the advisory lock
- **WHEN** apply runs
- **THEN** the system MUST append `apply_started` before executing
  statements
- **AND** MUST append `statement_ok` with that statement's ordinal after
  each success
- **AND** MUST append `version_applied` only after every statement succeeds
- **AND** MUST NOT claim the file was one transaction

#### Scenario: A semicolon inside a string stops before apply

- **GIVEN** a file whose statement parse sees a semicolon inside a string
  literal
- **WHEN** the operator validates the corpus
- **THEN** validation MUST fail
- **AND** apply MUST NOT start

#### Scenario: Comments are not statements

- **GIVEN** a full-line `--` comment, including a comment about recreating
  an object
- **WHEN** apply splits a version into statements
- **THEN** that comment MUST NOT be sent as SQL
- **AND** the system MUST NOT recreate objects because of the comment

### Requirement: Crash and partial failure stay fail-closed

A crash, a failed statement, or loss of the coordinator session between
`apply_started` and `version_applied` MUST leave the version `applying` or
`partial` and MUST fail closed. The system MUST NOT send the next
statement after that loss. Further apply of that version MUST stop until
an explicit operator reconciliation policy exists. The system MUST NOT
continue automatically from the middle of the file and MUST NOT roll the
successful statements back. After a process restart the system MUST read
the target ledger rather than process
memory or PostgreSQL. `partial` and `history_unresolved` MUST still forbid
a blind run after restart. Release of the advisory lock MUST happen after
the terminal audit event or after failure handling, or automatically when
the PostgreSQL session dies. A new authorization MUST NOT resume a partial
version from the middle and MUST NOT replay it.

#### Scenario: Crash after a successful statement leaves the version unclosed

- **GIVEN** `apply_started` is recorded and at least one statement has
  succeeded
- **WHEN** the process or the coordinator session stops before
  `version_applied`
- **THEN** the version MUST remain `partial` or `applying`
- **AND** already successful statements MUST remain in place
- **AND** the system MUST NOT roll them back
- **AND** the system MUST NOT send the next statement
- **AND** apply of that version MUST stop

#### Scenario: Restart does not continue a partial or unknown history

- **GIVEN** the ledger says `partial` or `history_unresolved`
- **WHEN** a new process starts, acquires the advisory lock, and reads the
  target
- **THEN** it MUST take that state from the ClickHouse ledger
- **AND** MUST NOT continue a blind run from memory
- **AND** MUST NOT read applied status from PostgreSQL
- **AND** MUST NOT resume the partial file from the middle

### Requirement: Exclusive mutation uses a PostgreSQL session advisory lock

Across all instances of this migration runner for the same target identity
(server UUID plus database `default_db`), at most one authorized runner
may mutate that target at a time. Mutating commands MUST be `ensure-ledger`,
reconcile, and apply. Each MUST acquire `pg_try_advisory_lock` or
`pg_advisory_lock` on a dedicated PostgreSQL session before the first
target statement and MUST keep that session alive through every target
mutation. The lock key MUST be a migration-control namespace key plus a
deterministic key of that server UUID and `default_db`. The namespace key
MUST NOT be the Alembic lock id `731984123`. The runner MUST NOT call
Alembic. The coordinator DSN MUST be explicit configuration. Every
authorized runner for the same target MUST be configured with that same
coordinator. Absence of the DSN MUST fail closed before target mutation.
The implementation MUST NOT fall back to application runtime DI, Redis, a
local file lock, `DATABASE_URL`, or a ClickHouse nonce. An append-only
ClickHouse table plus a read of the latest nonce MUST NOT be that
acquisition. A TTL lease without the live coordinator session MUST NOT be
that acquisition. If `pg_try_advisory_lock` returns false, the runner MUST
refuse with lock contention and MUST NOT send a statement. Loss of the
coordinator session or lock MUST stop further SQL and MUST leave an
in-flight version `applying` or `partial`. Status, validate, plan, and
inspect MUST NOT open the coordinator. A manual `clickhouse-client` session
is outside this runner. The system MUST state that caveat and MUST NOT
treat the caveat as proof that the runner is single-writer safe.

#### Scenario: Authorized ensure-ledger holds the advisory lock

- **GIVEN** an isolated target, explicit coordinator DSN, and the
  ensure-ledger authorization
- **WHEN** ensure-ledger runs
- **THEN** it MUST acquire the session advisory lock for that server UUID
  and `default_db` before creating the ledger
- **AND** MUST keep the session until the ledger creation is terminal or
  has failed
- **AND** MUST NOT mark `001`–`005` applied

#### Scenario: Missing coordinator fails closed

- **GIVEN** an isolated target and a mutating authorization flag
- **WHEN** ensure-ledger, reconcile, or apply is requested without an
  explicit coordinator DSN
- **THEN** the system MUST refuse with `blocked_missing_coordinator` before
  any target statement
- **AND** MUST NOT open the application database connection as a substitute

#### Scenario: Wrong coordinator is not this lock

- **GIVEN** a runner that would take the Alembic advisory lock id
  `731984123`, call `app.db.migrate`, or silently use application
  `DATABASE_URL`, Redis, a file lock, or a ClickHouse nonce
- **WHEN** a mutating command starts
- **THEN** the system MUST refuse before any target statement
- **AND** MUST NOT treat that other mechanism as the migration-control lock

#### Scenario: Lock contention sends no statement

- **GIVEN** two runner instances for the same server UUID and `default_db`
  configured with the same coordinator
- **WHEN** the second `pg_try_advisory_lock` returns false
- **THEN** that instance MUST refuse with `blocked_lock_contention`
- **AND** MUST NOT send a target statement
- **AND** MUST NOT treat a nonce read as exclusive acquisition

#### Scenario: Lock loss stops further SQL

- **GIVEN** a runner whose coordinator session dies after `apply_started`
  or after a `statement_ok`
- **WHEN** the next statement would be sent
- **THEN** it MUST NOT send that statement
- **AND** MUST leave the version `applying` or `partial`
- **AND** MUST NOT roll back a statement that already succeeded

### Requirement: This change mutates only an isolated target and does not touch production

This change MUST implement real mutating behavior for an isolated
non-production target: `ensure-ledger`, authorized reconcile, and
authorized apply of schema DDL `001`–`004`, each under the exclusive
PostgreSQL advisory lock. It MUST NOT connect to production, MUST NOT apply
migrations on production, and MUST refuse a production target class with
`blocked_production_target` until a future separate operator GO. It MUST
NOT hardcode production credentials, MUST NOT pass production credentials
into a port, MUST NOT open a production socket, and MUST NOT perform a live
network call. Isolated tests MUST use a substituted target port and a
substituted coordinator session. The change MUST NOT import the application
ClickHouse client and MUST NOT read application connection settings.
Readiness of this change MUST NOT be confirmed by a production apply and
MUST NOT require secrets, Kubernetes, or deployment.

#### Scenario: Isolated apply is real and production is untouched

- **GIVEN** an isolated executor with a substituted target port, a
  substituted coordinator session, no production credentials, and no
  production socket
- **WHEN** tests exercise authorized apply of schema DDL `001`–`004` after
  a baseline and under the held advisory lock
- **THEN** the runner MUST execute that schema DDL and append
  `version_applied` only after all statements succeed
- **AND** the system MUST NOT open a production connection
- **AND** MUST NOT perform a live network call

#### Scenario: Production target without a separate GO refuses

- **GIVEN** a target whose class is production, even with coordinator config
  and an apply authorization flag
- **WHEN** ensure-ledger, reconcile, or apply is requested
- **THEN** the system MUST refuse with `blocked_production_target` before
  any statement
- **AND** MUST NOT treat this change as the future operator GO

#### Scenario: The application client is not the migration executor

- **GIVEN** the application ClickHouse client and its connection settings
- **WHEN** the migration control plane is built and tested
- **THEN** it MUST NOT use that client
- **AND** MUST NOT read those settings
- **AND** MUST NOT take production credentials from them

### Requirement: Alembic and test DDL are not a second corpus

PostgreSQL Alembic MUST NOT become the ClickHouse migration system. The
system MUST NOT store this ledger in Alembic and MUST NOT move `001`–`005`
into Alembic revisions. The Alembic advisory lock MUST NOT be reused as
this coordinator. Session DDL for `test_adv_bot_clickhouse` MUST NOT enter
the corpus fingerprint. The control plane MUST NOT use the test seam that
rewrites `default_db` names into the test database. Expanding ClickHouse
use in shop-wide campaign data collection MUST NOT start until this
migration lifecycle is in order. This change MUST NOT perform that
expansion.

#### Scenario: Alembic stays out of ClickHouse migrations

- **GIVEN** the existing PostgreSQL Alembic history and its advisory lock
- **WHEN** the ClickHouse corpus, ledger, and coordinator are defined
- **THEN** Alembic MUST NOT own ClickHouse versions
- **AND** MUST NOT store `default_db.ch_schema_migration_ledger`
- **AND** MUST NOT contain `001`–`005` as its revisions
- **AND** its lock id MUST NOT be the migration-control namespace key

#### Scenario: Test DDL is not canonical

- **GIVEN** session DDL that creates objects in `test_adv_bot_clickhouse`
  and a test seam that rewrites `default_db` names
- **WHEN** the corpus fingerprint is built
- **THEN** that test DDL MUST NOT be part of the fingerprint
- **AND** the control plane MUST NOT use that rewrite seam
- **AND** `001`–`004` MUST still name `default_db`

#### Scenario: Shop-wide expansion waits

- **GIVEN** this migration lifecycle is the change under test
- **WHEN** readiness of the change is judged
- **THEN** shop-wide campaign data collection MUST NOT start as part of
  this change
- **AND** readiness MUST NOT depend on a production migration, secrets,
  Kubernetes, or deployment
