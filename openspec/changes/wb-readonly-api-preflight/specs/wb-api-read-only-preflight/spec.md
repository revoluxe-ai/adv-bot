# Capability: wb-api-read-only-preflight

Operator-facing read-only WB API preflight/collect for a given `shop_id`,
run via `/opsx-scripts` Job in Owner-bot runtime, with Owner-local research
archive (secret-strip only). Not a Web CLEAN_DUMP / Stage B accept gate.

## Requirements

### Requirement: Modes preflight and collect

The system SHALL expose a scripts entrypoint that accepts required `--shop-id`
and `--mode` with values `preflight` or `collect`.

#### Scenario: Preflight smallest probe

- **WHEN** operator runs with `--mode preflight` and a valid `--shop-id`
- **THEN** the Job SHALL perform the smallest read-only probe covering the four
  endpoint-family aliases (ads, cards, analytics, norms) via existing WB API
  stack only
- **AND** SHALL produce a structured report of per-family status
- **AND** SHALL NOT perform create/update/delete/finance mutation writes

#### Scenario: Collect best-effort pull

- **WHEN** operator runs with `--mode collect` and a valid `--shop-id`
- **THEN** the Job SHALL best-effort collect read-only data for the same four
  families within a bounded retry/run budget
- **AND** MAY complete with PARTIAL status when some families or pages fail
- **AND** MUST include an honest gap report for missing/failed parts
- **AND** MUST NOT report overall full success when gaps remain
- **AND** SHALL NOT perform create/update/delete/finance mutation writes

### Requirement: Existing stack and bounded retries

The system SHALL obtain access via existing Owner-bot mechanisms
(e.g. `get_access_for_wb_cabinet`) and call WB only through existing
`app/core/mp/wb/api` managers/adapters. The system SHALL NOT introduce a new
raw WB HTTP client. Retries, rate-limits, and timeouts SHALL reuse shop-runner
(or equivalent production) WB API patterns, with a finite ceiling for the whole
run so the Job cannot hang indefinitely.

#### Scenario: Retry then stop

- **WHEN** a transient WB/API error occurs during preflight or collect
- **THEN** the system MAY retry according to production patterns
- **AND** MUST stop within the configured run ceiling and record the failure
  in the report/gaps

#### Scenario: No invent URL

- **WHEN** an endpoint family has no existing manager/adapter mapping
- **THEN** the system SHALL record a gap for that family
- **AND** SHALL NOT invent or hardcode a new WB URL outside the existing stack

### Requirement: READ_ONLY_NO_MUTATION policy

The system SHALL enforce `READ_ONLY_NO_MUTATION`: mutation writes
(create/update/delete and finance write paths) are forbidden. HTTP POST used
solely for read/query semantics is allowed.

#### Scenario: Mutation refused

- **WHEN** a code path would perform a mutation write against WB
- **THEN** the system SHALL refuse that path for this entrypoint
- **AND** SHALL record the refusal or prevent compilation/use of that path

### Requirement: Owner-local L0 archive (secret-strip)

On successful Job completion (including PARTIAL collect), the system SHALL
produce an Owner-local research archive containing payload data and the
structured report (and SHOULD include sha256 of archive contents). The archive
MUST strip secrets: tokens, Authorization headers, cookies MUST NOT appear in
payload files, report, or Job logs. Web-grade sanitization of business IDs /
body redaction and quarantine→transfer are out of scope.

#### Scenario: Secret-strip on archive

- **WHEN** the Job writes outputs for copy to the operator machine
- **THEN** outputs and logs MUST NOT contain WB API tokens or Authorization
  material
- **AND** `/opsx-scripts` SHALL copy the archive and report an absolute local
  path to the operator

#### Scenario: No Web PASS claim

- **WHEN** preflight or collect finishes
- **THEN** the system MUST NOT claim Web `READ_ONLY_PREFLIGHT_PASS` or Web
  CLEAN_DUMP acceptance
- **AND** the report SHALL describe the result as Owner-local research dump /
  ops status only

### Requirement: Job-only API runtime

WB API calls SHALL execute only inside the Owner-bot Job runtime. The Cursor
agent SHALL plan, apply Job, wait, and copy outputs — and SHALL NOT call
production WB API from the local agent session.

#### Scenario: Cursor does not call WB

- **WHEN** operator drives the flow via `/opsx-scripts`
- **THEN** WB credentials and HTTP to WB SHALL occur only in-cluster Job
- **AND** local agent steps are limited to kubectl/plan/cp/report

### Requirement: Shop binding by argument

Pilot shop «Дилера» (`bab6bc8e-8123-4559-862e-5da3a8ed5b69`) MAY be used as
the battle-test argument. The entrypoint MUST NOT hardcode that shop_id as the
only supported shop; `shop_id` is always an operator argument.

#### Scenario: Arbitrary shop_id

- **WHEN** operator passes a different valid `--shop-id`
- **THEN** the same modes and archive behavior SHALL apply for that shop

## Non-requirements (this capability)

- Web L2 sanitize / quarantine→transfer / Web CLEAN_DUMP contract
- Swagger sync, API Master, read-only token hardening
- Finance or mutation write tooling
- Declaring Web Stage B accept gates
