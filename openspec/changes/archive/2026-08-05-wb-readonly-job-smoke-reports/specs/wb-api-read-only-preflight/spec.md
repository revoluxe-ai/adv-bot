## MODIFIED Requirements

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

## ADDED Requirements

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

#### Scenario: Prod Job evidence is out of this change capability

- **WHEN** this delta capability is evaluated for OpenSpec change completion
- **THEN** successful prod `/opsx-scripts` Job, Owner-local archive copy, and
  cluster ledger updates MUST NOT be required as acceptance of this change
- **AND** live Job+real-data proof remains owned by the scripts/evolution lane
  (INC-RO-07), not by `/opsx-apply` tasks for this change
