## ADDED Requirements

### Requirement: ORDERS_OR_SALES_REPORTS_READ family

The system SHALL treat `ORDERS_OR_SALES_REPORTS_READ` as a distinct
endpoint-family alias meaning supplier orders and/or sales report reads from
the WB Statistics/Reports API surface (`GET` supplier orders and, when used,
supplier sales). The operator preflight/collect path MUST include this family
and MUST execute it first among families in preflight order.

#### Scenario: Preflight runs ORDERS family first

- **WHEN** operator runs with `--mode preflight` and a valid `--shop-id`
- **THEN** the Job SHALL probe `ORDERS_OR_SALES_REPORTS_READ` before other
  endpoint-family aliases
- **AND** SHALL record per-family status for ORDERS in the structured report

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

Operator/read-only entrypoints MUST expose only the supplier orders GET (and
supplier sales GET when enabled for the same family) through domain adapters;
other operations present in the full generated Reports client MUST NOT be
invoked by this preflight/collect path.

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

- **WHEN** `wb-api-read-only-preflight` runs ORDERS family work
- **THEN** it MUST only request supplier orders GET and optionally supplier
  sales GET for that family
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
   GET and optional supplier sales GET into the hub/managers used by
   preflight/collect.

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
semantics per API), at most one successful first-page response, and
MUST NOT follow `lastChangeDate` continuation/pagination in preflight.
The contract window start `2026-07-04` MUST be applied as `dateFrom` when
operating under the COL-R03 pilot period. The system MUST NOT silently use
yesterday→today as a substitute for that window. Period semantics recorded in
the report/mapping attestation MUST NOT claim a classic exact start+end query
model if the API only supports `dateFrom`/cursor continuation.

#### Scenario: Preflight single page from dateFrom

- **GIVEN** pilot period start `2026-07-04` (Europe/Moscow)
- **WHEN** preflight probes ORDERS
- **THEN** the request SHALL use `dateFrom` aligned to that start
- **AND** SHALL NOT follow a next page or `lastChangeDate` continuation
- **AND** the report/attestation SHALL describe dateFrom/first-page semantics
  honestly

#### Scenario: Forbidden silent yesterday-today for ORDERS

- **WHEN** preflight runs ORDERS under the pilot period rules
- **THEN** the system MUST NOT substitute a default yesterday→today range in
  place of the attested `dateFrom` window start

## MODIFIED Requirements

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
