# Capability: wb-api-read-only-preflight

<!-- Synced from change wb-readonly-job-smoke-reports on archive 2026-08-05;
     prior: statistics-orders-sales-get-adapter / wb-readonly-api-preflight -->

Operator-facing read-only WB API preflight/collect for a given `shop_id`,
run via `/opsx-scripts` Job in Owner-bot runtime, with Owner-local research
archive (secret-strip only). Not a Web CLEAN_DUMP / Stage B accept gate.

## Requirements

### Requirement: Modes preflight and collect

The system SHALL expose a scripts entrypoint that accepts required `--shop-id`
and `--mode` with values `preflight` or `collect`.

#### Scenario: Preflight smallest probe

- **WHEN** operator runs with `--mode preflight` and a valid `--shop-id`
- **THEN** the Job SHALL perform the smallest read-only probe covering the
  endpoint-family aliases including `ORDERS_OR_SALES_REPORTS_READ` first, then
  the remaining families (campaigns/cards/analytics/norms as mapped) via the
  existing WB API stack only
- **AND** SHALL produce a structured report of per-family status
- **AND** SHALL NOT perform create/update/delete/finance mutation writes

#### Scenario: Collect best-effort pull

- **WHEN** operator runs with `--mode collect` and a valid `--shop-id`
- **THEN** the Job SHALL best-effort collect read-only data for the same
  families (including ORDERS) within a bounded retry/run budget
- **AND** MAY complete with PARTIAL status when some families or pages fail
- **AND** MUST include an honest gap report for missing/failed parts
- **AND** MUST NOT report overall full success when gaps remain
- **AND** SHALL NOT perform create/update/delete/finance mutation writes

### Requirement: Existing stack and bounded retries

The system SHALL obtain access via existing Owner-bot mechanisms
(e.g. `get_access_for_wb_cabinet`) and call WB only through existing
`app/core/mp/wb/api` managers/adapters, including the versioned generated
Reports client for ORDERS. The system SHALL NOT introduce a new raw WB HTTP
client. Retries, rate-limits, and timeouts SHALL reuse shop-runner
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
  (for ORDERS: outside the generated Reports client + adapters)

### Requirement: ORDERS_OR_SALES_REPORTS_READ family

The system SHALL treat `ORDERS_OR_SALES_REPORTS_READ` as a distinct
endpoint-family alias meaning supplier orders **and** supplier sales report
reads from the WB Statistics/Reports API surface (`GET` supplier orders and
`GET` supplier sales). For Stage A preflight/collect of this capability, the
operator path MUST request **both** GETs (not orders-only). The operator
preflight/collect path MUST include this family and MUST execute it first among
families in preflight order.

#### Scenario: Preflight runs ORDERS family first

- **WHEN** operator runs with `--mode preflight` and a valid `--shop-id`
- **THEN** the Job SHALL probe `ORDERS_OR_SALES_REPORTS_READ` before other
  endpoint-family aliases
- **AND** SHALL record per-family status for ORDERS in the structured report

#### Scenario: Stage A requests orders and sales

- **WHEN** preflight or collect runs `ORDERS_OR_SALES_REPORTS_READ` under
  Stage A rules
- **THEN** the Job SHALL perform supplier orders GET and supplier sales GET
- **AND** SHALL record distinct orders and sales outcomes (counts and/or gaps)
  in the structured report for that family
- **AND** MUST NOT treat orders-only success as complete Stage A satisfaction
  of the family when sales was not attempted

#### Scenario: No substitute sources for ORDERS

- **WHEN** the Job evaluates or reports `ORDERS_OR_SALES_REPORTS_READ`
- **THEN** it MUST NOT treat analytics sales-funnel, search-report product
  orders, promotion campaign statistics order metrics, or marketplace
  assembly-order APIs as satisfying that family
- **AND** MUST NOT mark ORDERS as successful solely because those other
  sources returned data

### Requirement: Versioned Reports OpenAPI client for ORDERS access

Access to `ORDERS_OR_SALES_REPORTS_READ` SHALL be provided only through a
**fully generated**, versioned WB Reports OpenAPI client derived from the
official Reports OpenAPI specification (English `12-reports` YAML when used as
source of truth for this capability), integrated into the existing WB API
stack. The system MUST NOT invent Statistics/Reports URLs or call that host via
an ad-hoc raw HTTP client outside the generated client + stack adapters.

Each generated version MUST retain:

- the source OpenAPI YAML used for generation;
- a fingerprint lock of that specification (hash and source metadata).

A version without retained source YAML and fingerprint lock MUST NOT be treated
as the authoritative client for this family.

The project’s standard WB OpenAPI client generator MUST gain a mapped Reports
target (alongside existing promotion/products mappings). Generation SHALL follow
the same rules as other WB clients:

- choose the mapped Reports key;
- persist YAML under the new version’s swagger artifacts (or use cached YAML
  with explicit version when regenerating offline);
- run OpenAPI client generation into that version without deleting prior
  versions;
- for English Reports YAML, skip transliteration; for Russian YAML, transliterate
  before generation when required by the generator toolchain.

Preferred offline regeneration for this change uses the Owner-local swagger
inventory Reports English YAML as the cached spec input so generation does not
depend on live download during apply.

Operator/read-only entrypoints MUST expose only the supplier orders GET and
supplier sales GET through domain adapters for this family; other operations
present in the full generated Reports client MUST NOT be invoked by this
preflight/collect path. Stage A of this capability MUST invoke both exposed
GETs (orders and sales).

#### Scenario: ORDERS uses generated Reports client

- **WHEN** preflight or collect performs `ORDERS_OR_SALES_REPORTS_READ`
- **THEN** the call SHALL go through the existing WB API stack backed by the
  versioned generated Reports client
- **AND** SHALL NOT use a one-off raw HTTP client with a hardcoded Statistics
  URL invented outside that generated client

#### Scenario: Generated version has swagger lock artifacts

- **WHEN** a Reports client version is introduced or regenerated for ORDERS
- **THEN** that version MUST include the source OpenAPI YAML and a fingerprint
  lock
- **AND** prior client versions MUST remain intact (new version, not in-place
  wipe of older versions)

#### Scenario: Offline regenerate from inventory Reports YAML

- **WHEN** engineers regenerate the Reports client using the standard generator
  with cached Official Reports YAML (inventory snapshot) and an explicit
  version
- **THEN** generation MUST succeed without inventing endpoints
- **AND** the resulting client MUST still be the sole stack basis for ORDERS
  family calls

#### Scenario: Narrow surface for operator path

- **WHEN** `wb-api-read-only-preflight` runs ORDERS family work under Stage A
- **THEN** it MUST request supplier orders GET and supplier sales GET for that
  family
- **AND** MUST NOT call other Reports-client operations (finances-adjacent,
  acceptance, region-sale, and similar) from this entrypoint

### Requirement: Reports client generation procedure (INC-RO-06)

Extending the WB stack for ORDERS MUST follow the project WB OpenAPI client
generation procedure (same contract as documented for promotion/products
clients in the generated-clients guide):

1. Register a Reports mapping in the standard generator targets (key such as
   `reports`), pointing at official English Reports OpenAPI YAML
   (`12-reports.yaml` / portal English reports YAML), package name for the
   generated Reports client, target root under the versioned generated tree,
   transliteration **off** for English source.
2. Produce a new `vN` (do not destroy older versions).
3. Ensure `vN` swagger artifacts include source YAML + fingerprint lock.
4. Prefer cached-spec mode with an explicit version when generating from the
   Owner-local swagger inventory snapshot of English `12-reports.yaml`
   (avoids live portal download during apply).
5. Optional remote fingerprint check against the portal is allowed later for
   refresh workflows; it is not required to claim ORDERS family ready if
   inventory YAML + lock are present.
6. After generation, wire domain adapters that expose **only** supplier orders
   GET and supplier sales GET into the hub/managers used by preflight/collect
   (Stage A MUST invoke both).

#### Scenario: Generator mapping for Reports exists

- **WHEN** INC-RO-06 is implemented
- **THEN** the standard WB OpenAPI client generator MUST accept a Reports
  spec-key analogous to `promotion` / `products`
- **AND** English Reports YAML MUST be the configured source for that key
  (no transliteration)

#### Scenario: Cached inventory generate is valid

- **GIVEN** Owner-local swagger inventory contains English `12-reports.yaml`
- **WHEN** generation runs with cached-spec mode and an explicit version
- **THEN** a complete `vN` client with YAML + lock MUST be produced
- **AND** that client MUST be what ORDERS family calls use

### Requirement: ORDERS period attestation (dateFrom / first page)

For Stage A / preflight of `ORDERS_OR_SALES_REPORTS_READ`, the system SHALL use
the Statistics/Reports period model honestly: required `dateFrom` (Europe/Moscow
semantics per API) for **both** supplier orders and supplier sales requests, at
most one successful first-page response per request, and MUST NOT follow
`lastChangeDate` continuation/pagination in Stage A. The contract window start
`2026-07-04` MUST be applied as `dateFrom` when operating under the COL-R03
pilot period. The system MUST NOT silently use yesterday→today as a substitute
for that window. Period semantics recorded in the report/mapping attestation
MUST NOT claim a classic exact start+end query model if the API only supports
`dateFrom`/cursor continuation.

#### Scenario: Preflight single page from dateFrom

- **GIVEN** pilot period start `2026-07-04` (Europe/Moscow)
- **WHEN** preflight probes ORDERS (orders and sales)
- **THEN** each Stage A request SHALL use `dateFrom` aligned to that start
- **AND** SHALL NOT follow a next page or `lastChangeDate` continuation
- **AND** the report/attestation SHALL describe dateFrom/first-page semantics
  honestly for the family

#### Scenario: Forbidden silent yesterday-today for ORDERS

- **WHEN** preflight runs ORDERS under the pilot period rules
- **THEN** the system MUST NOT substitute a default yesterday→today range in
  place of the attested `dateFrom` window start

### Requirement: Stage A family status when sales fails after orders

When Stage A supplier orders GET succeeds and supplier sales GET fails, the
family status MUST be PARTIAL (not overall family success), and the structured
report MUST include an honest gap for sales while retaining orders evidence.
When supplier orders GET fails, the family status MUST be FAILED (or equivalent
non-success) and MUST record the orders failure.

#### Scenario: Sales failure yields PARTIAL with orders retained

- **GIVEN** Stage A supplier orders GET returns successfully
- **WHEN** supplier sales GET fails
- **THEN** the family status MUST be PARTIAL
- **AND** the report MUST include a sales gap
- **AND** MUST still record orders outcome data for the family

#### Scenario: Orders failure is non-success

- **WHEN** Stage A supplier orders GET fails
- **THEN** the family status MUST NOT be reported as full success
- **AND** the report MUST include an orders failure or gap

### Requirement: Targeted automated coverage for ORDERS+sales Stage A

The system SHALL have targeted automated tests (without live production WB API)
that cover Stage A `ORDERS_OR_SALES_REPORTS_READ` behavior for both supplier
orders and supplier sales, including attestation fields
(`dateFrom` / first-page / no next-page follow) and honest PARTIAL/gap behavior
when a page is empty or a call fails.

#### Scenario: Unit coverage without live WB

- **WHEN** the targeted automated suite for this capability runs
- **THEN** it MUST exercise ORDERS+sales Stage A paths without calling live
  production WB API
- **AND** MUST assert that both orders and sales are requested under Stage A
- **AND** MUST assert first-page / no-pagination attestation semantics

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
