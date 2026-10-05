# ai-package-v1-exporter Specification

## Purpose

Bounded read-only AI Package v1: export accumulated shop datasets for a period
into a versioned artifact bundle (domain contract independent of ZIP encoding).
Synced from change `ai-package-v1-contract` (archived 2026-10-01).
## Requirements
### Requirement: Export input and shop scope

The exporter MUST accept `shop_id` and a bounded period `[period_start, period_end]`
(inclusive calendar dates in shop export timezone — fixed in implementation).
Export MUST be scoped to that shop only. Cross-shop rows MUST NOT appear in
outputs or manifest scope.

#### Scenario: Single shop bounded period

- **GIVEN** a connected shop with `shop_id` S and period P
- **WHEN** export runs for (S, P)
- **THEN** every dataset row and manifest scope field MUST reference only S
- **AND** rows outside P MUST NOT be included unless explicitly marked as
  coverage gap metadata (not as data rows)

#### Scenario: Shop isolation

- **GIVEN** shops S1 and S2 with data in PG/CH
- **WHEN** export runs for S1
- **THEN** no row, file, or manifest entry MUST contain S2 identifiers or data

### Requirement: Read-only accumulated sources only

Export MUST read only already accumulated PostgreSQL and ClickHouse. Export MUST
NOT invoke WB API, MUST NOT start shop-wide collection, collectors, backfill,
or CSV poller. Missing accumulation MUST surface as `coverage` and
`reason_codes`, not silent success.

#### Scenario: No WB API on export path

- **GIVEN** export is invoked
- **WHEN** datasets are loaded
- **THEN** no WB HTTP client, adapter, or collector entrypoint MUST run on the
  export path

#### Scenario: Missing accumulation is explicit

- **GIVEN** a dataset has no rows in PG/CH for P
- **WHEN** export completes
- **THEN** `collection_outcome` and `coverage` MUST reflect the gap
- **AND** export MUST NOT claim full `coverage` from empty success alone

### Requirement: Domain contract separate from ZIP transport

Manifest fields, dataset cards, coverage semantics, and row payloads MUST be
defined as a versioned domain contract (`package_schema_version`). ZIP MUST be
a transport encoding of that contract (files + manifest). Validator logic MUST
apply to the domain contract and MUST NOT depend on compression or archive
library specifics beyond listed file names and hashes.

#### Scenario: Same domain different transport

- **GIVEN** two transports encode the same manifest and payload bytes
- **WHEN** validator runs on domain manifest
- **THEN** validation outcome MUST be identical

### Requirement: Campaign full stat dataset

Campaign full statistics MUST be read from ClickHouse
`default_db.full_adv_wb_stat` at grain `campaign_id` (`adv_id`) + `date`. Rows
MUST preserve source grain. Campaign-level stats MUST NOT be allocated to
`nm_id` without source-confirmed breakdown.

#### Scenario: Campaign date grain preserved

- **GIVEN** rows exist in `default_db.full_adv_wb_stat` for campaigns of shop S
- **WHEN** campaign full stat dataset is exported for P
- **THEN** each exported row MUST retain `campaign_id` and `date` grain
- **AND** MUST NOT include fabricated per-`nm_id` breakdown

#### Scenario: Auto and Search remain separate original rows

- **GIVEN** a ComplexAdv pair with distinct Auto (shelf) and Search (keywords)
  `campaign_id`s
- **WHEN** campaign full stat is exported
- **THEN** each side MUST appear as separate original rows
- **AND** MUST NOT be merged into one indistinguishable campaign row without
  an explicit labeled derivative aggregate file (derivative aggregates MAY exist
  only when spec for aggregates applies; default export is separate originals)

### Requirement: Common funnel dataset scoped to ComplexAdv main nmid

Common / funnel statistics MUST be read from ClickHouse `default_db.wb_common_stat`
only for `nmid` equal to `ComplexAdv.main_nmid` for each in-scope campaign of
shop S. Export MUST NOT treat `wb_common_stat` as a shop-wide product order feed
or as shop product orders/sales.

#### Scenario: Funnel limited to main nmid per ComplexAdv

- **GIVEN** shop S with ComplexAdv instances and their `main_nmid` values
- **WHEN** funnel dataset is exported for P
- **THEN** only rows with `nmid` in that main-nmid set MUST be included
- **AND** other shop `nmid`s MUST NOT be included

#### Scenario: Funnel orders are not shop product orders

- **GIVEN** funnel rows contain `orders` metrics
- **WHEN** shop product orders/sales dataset is emitted
- **THEN** funnel `orders` MUST NOT populate shop product orders/sales

### Requirement: PostgreSQL campaign inventory and relations (minimal v1)

The export MAY include a PostgreSQL **campaign inventory / relations** dataset
(manifest card id `campaign_settings_snapshot`) with **only** minimal
shop-scoped fields: `AdvSetting` rows joined to `WBCabinet.shop_id`, campaign
identifiers, and Auto/Search id linkage per repo evidence. Export MUST NOT
treat this dataset as a **detailed** field-level advertising **settings**
snapshot. Full detailed settings export is **out of v1** (future change
`ai-package-campaign-settings-snapshot`).

Inclusion requires a proven read-only PG seam (`get_async_session_maker(read_only=True)`,
shop-scoped SELECT only, no WB writes, no `WBShopDataManager` orchestrator).
When the seam is not defensible at apply time, export MUST emit dataset-level
`UNKNOWN` or omit with explicit `reason_codes`, not fabricated inventory or
detailed settings rows. When included with partial discovery, `coverage` MUST
reflect **PARTIAL** inventory (not FULL WB cabinet campaign universe).

#### Scenario: PG inventory is read-only minimal grain

- **GIVEN** PG inventory dataset is enabled per design
- **WHEN** export reads PG for shop S
- **THEN** only SELECT/read-only session patterns MUST be used
- **AND** `bot_active`, mode defaults, or WB write side effects MUST NOT occur
- **AND** rows MUST represent shop-scoped inventory/relations only (not full
  detailed settings field export)

#### Scenario: Detailed settings not implied by inventory card

- **GIVEN** v1 export for shop S
- **WHEN** manifest describes `campaign_settings_snapshot`
- **THEN** export MUST NOT claim complete detailed advertising settings coverage
- **AND** absence of detailed settings MUST NOT be masked as FULL settings snapshot

### Requirement: Shop product orders and sales unassigned

Shop product orders/sales source MUST be emitted as explicitly unassigned:
manifest MUST include `SOURCE_NOT_ASSIGNED` and/or dataset-level `UNKNOWN`.
Export MUST NOT use supplier GET, funnel orders, ad/campaign orders, or
`wb_common_stat` orders as a stand-in for shop product orders/sales.

#### Scenario: Explicit unassigned source

- **WHEN** shop product orders/sales dataset is materialized
- **THEN** source identity MUST be `SOURCE_NOT_ASSIGNED` or `UNKNOWN`
- **AND** MUST NOT assert supplier GET or funnel/ad orders as the source

### Requirement: Four independent completeness dimensions

Each dataset card and package summary MUST carry independent
`collection_outcome`, `coverage`, `reason_codes`, and `freshness`. They MUST NOT
substitute for each other. `NO_DATA` MUST NOT automatically imply incomplete
`coverage`. `UNKNOWN` MUST NOT be treated as success or full `coverage`
(fail-closed). Multiple `reason_codes` MAY apply simultaneously.

#### Scenario: NO_DATA without automatic incomplete coverage

- **GIVEN** `reason_codes` includes `NO_DATA`
- **WHEN** `coverage` is evaluated
- **THEN** `NO_DATA` alone MUST NOT force incomplete `coverage` without separate
  coverage evidence

#### Scenario: UNKNOWN fail-closed

- **GIVEN** a field is `UNKNOWN`
- **WHEN** consumer interprets export success
- **THEN** `UNKNOWN` MUST NOT count as success or full `coverage`

### Requirement: Capabilities and access metadata per shop

Export MUST include machine-readable scope metadata: shop capabilities relevant
to export (read-only), dataset access flags, and subscription/permission gaps as
`reason_codes` when evidence exists in PG. Export MUST NOT invent numeric WB API
limits or imply full history from latest timestamp alone.

#### Scenario: No fake coverage from timestamps

- **GIVEN** latest row timestamp is T
- **WHEN** history before P is missing
- **THEN** export MUST NOT mark full period `coverage` based on T alone

#### Scenario: No fabricated WB limits

- **WHEN** manifest describes collection windows
- **THEN** unverified vendored OpenAPI numeric limits MUST NOT appear as normative
  MUST windows

### Requirement: Versioned manifest with sha256

Export MUST produce `package_schema_version`, manifest listing each payload file
with `sha256`, byte size, and logical dataset id. Manifest MUST be deterministic
for identical inputs (stable ordering, stable serialization).

#### Scenario: Deterministic sha256

- **GIVEN** identical PG/CH snapshot inputs and export parameters
- **WHEN** export runs twice
- **THEN** per-file `sha256` and manifest hash MUST match
