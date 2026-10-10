# attribution-facts-contract Specification

## Purpose
TBD - created by archiving change attribution-facts-contract. Update Purpose after archive.
## Requirements
### Requirement: Canonical attribution fact grain

The system SHALL persist attribution commerce facts at grain:

`shop_id × physical_adv_id × event_date × app_type × ordered_nm_id`.

`advertised_nm_id` MUST NOT be part of the canonical fact key. `physical_adv_id`
MUST be the WB `advertId`. Auto and Search MUST remain separate physical adv_ids
per `grain-preservation`.

#### Scenario: Fact key excludes advertised nm

- **WHEN** a fact is stored for an attributed order on nm 14824677
- **AND** the campaign promotes multiple nm ids
- **THEN** the fact key MUST include `ordered_nm_id` only
- **AND** MUST NOT require a single `advertised_nm_id` field in the key

### Requirement: DIRECT classification

A fact SHALL be classified DIRECT when `ordered_nm_id` is a member of
`promoted_nm_ids` from an authoritative `MembershipSnapshot` covering
`(shop_id, physical_adv_id, event_date)`.

#### Scenario: Direct membership

- **GIVEN** promoted_nm_ids = {837395782} for adv_id 39900256 on 2026-09-07
- **WHEN** attributed_orders > 0 for ordered_nm_id 837395782
- **THEN** classification MUST be DIRECT

### Requirement: LINKED classification

A fact SHALL be classified LINKED when membership snapshot covers the date,
`promoted_nm_ids` is non-empty, the nm breakdown row exists, and
`ordered_nm_id ∉ promoted_nm_ids`. V1 MUST NOT require a separate linked-assortment
graph.

#### Scenario: Associated nm in fullstats tree

- **GIVEN** promoted_nm_ids = {837395782}
- **WHEN** attributed_orders > 0 for ordered_nm_id 14824677 in the same adv/day
- **THEN** classification MUST be LINKED

#### Scenario: Empty promoted set

- **GIVEN** promoted_nm_ids = ∅ for the date
- **WHEN** nm breakdown rows exist
- **THEN** classification MUST be UNKNOWN
- **AND** MUST NOT be LINKED

### Requirement: UNKNOWN and fail-closed economics

When membership is missing, empty, or ambiguous, classification MUST be UNKNOWN.
Implementations MUST NOT emit numeric DIRECT or LINKED CPO/DRR for that scope.
MUST NOT fallback LINKED to DIRECT.

#### Scenario: Missing membership snapshot

- **WHEN** no covering snapshot exists for event_date
- **THEN** classification MUST be UNKNOWN
- **AND** reason_codes MUST include `ATTRIBUTION_RELATION_UNKNOWN`

### Requirement: Missing attribution is not zero

Missing facts, UNKNOWN classification, or GAP coverage MUST NOT be represented
as numeric zero for attributed orders or GMV.

#### Scenario: No nm rows

- **WHEN** no authoritative nm breakdown exists for adv/day
- **THEN** attributed_orders MUST be absent or explicit GAP
- **AND** MUST NOT be 0 solely due to absence

### Requirement: Spend authority separation

Canonical campaign-day spend MUST remain `default_db.full_adv_wb_stat`.
Attribution facts MUST NOT duplicate authoritative spend ownership. CPO and DRR
MUST join spend once per `(physical_adv_id, event_date)`.

#### Scenario: Single spend join

- **WHEN** computing CPO_FACT_DIRECT for a window
- **THEN** spend numerator MUST come from full_adv_wb_stat latest per adv/day
- **AND** MUST NOT sum nm-level spend with campaign-day spend for the numerator

### Requirement: Revision and correction semantics

Observations MUST be append-only. Identical payload hash MUST NOT create duplicate
logical facts. A corrected WB restatement MUST append a new observation and
replace the prior value in the latest projection. Implementations MUST NOT sum
old and new observations for the same fact key.

#### Scenario: Restated day

- **WHEN** a second observation arrives with different orders for the same fact key
- **THEN** latest projection MUST reflect the new observation only once

### Requirement: Reconciliation

For each `(physical_adv_id, event_date)` with COMPLETE coverage, sum of nm
`attributed_orders` MUST equal campaign-day orders and sum of nm GMV MUST match
day sum_price within configured ε. DIRECT + LINKED + UNATTRIBUTED orders MUST
equal day orders when UNATTRIBUTED bucket is used.

#### Scenario: Reconciliation pass

- **GIVEN** nm breakdown sums match day totals
- **WHEN** coverage is evaluated
- **THEN** reconciliation status MUST be PASS

#### Scenario: No supplier reconciliation

- **WHEN** evaluating attribution completeness
- **THEN** supplier ORDERS/SALES and wb_common_stat MUST NOT be used as reconciliation denominators

### Requirement: Coverage and package cutoff

Attribution coverage MUST use independent dimensions per `coverage-provenance`.
`package_cutoff_date` MUST NOT automatically imply `COMPLETE`. DIRECT/LINKED
numeric metrics MUST require `COMPLETE` coverage and reconciliation PASS for every
day in the window intersection.

#### Scenario: Cutoff without source proof

- **GIVEN** package_cutoff_date = 2026-10-05
- **AND** source_complete_through = 2026-09-25
- **WHEN** a 1d window ends on package_cutoff_date
- **THEN** coverage MUST NOT be COMPLETE solely due to cutoff alignment

### Requirement: Derived metrics

CPO_FACT_DIRECT, CPO_FACT_LINKED, DRR_FACT_DIRECT, DRR_FACT_LINKED MUST use
window-aggregated DIRECT/LINKED numerators and joined spend. Zero denominator
MUST yield absent metric with `DENOMINATOR_ZERO`, not numeric zero.

#### Scenario: Zero direct orders

- **WHEN** DIRECT attributed_orders sum is 0
- **THEN** CPO_FACT_DIRECT MUST be absent
- **AND** reason_codes MUST include `DENOMINATOR_ZERO`

### Requirement: Unsupported buyouts

Attributed buyouts at nm grain MUST be UNSUPPORTED in V1 unless a new factual
source is accepted by spec amendment.

#### Scenario: Buyout request

- **WHEN** consumer requests attributed_buyouts
- **THEN** response MUST be UNSUPPORTED with `ATTRIBUTION_UNSUPPORTED`

### Requirement: AttributionFactsReader port

Consumers (AI Package analysis, future MCP) MUST depend on `AttributionFactsReader`
returning facts, coverage metadata, and reconciliation summaries without exposing
physical storage details.

#### Scenario: Analysis consumer

- **WHEN** AnalysisAggregationService queries attribution for a scope and window
- **THEN** it MUST use AttributionFactsReader
- **AND** MUST NOT read ClickHouse attribution tables directly

### Requirement: Auto Search pair aggregation

Aggregating attribution across Auto and Search physical adv_ids for one ComplexAdv
MUST be opt-in. Without overlap proof, implementations MUST fail closed with
`ATTRIBUTION_SCOPE_MISMATCH`.

#### Scenario: Default leg isolation

- **WHEN** consumer does not request pair aggregate
- **THEN** facts MUST remain isolated per physical_adv_id

### Requirement: Membership precedence

MembershipSnapshot resolution MUST follow:

1. `campaign_settings_history` as-of event_date
2. `shop_campaign_inventory.nm_ids` bounded fallback
3. collect-time WB `nm_settings` in observation provenance

#### Scenario: History preferred

- **GIVEN** history snapshot covers event_date
- **WHEN** resolving promoted_nm_ids
- **THEN** history MUST be used
- **AND** inventory fallback MUST NOT override history

