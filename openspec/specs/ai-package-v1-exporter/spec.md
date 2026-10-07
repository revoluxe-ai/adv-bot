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
(manifest card id `campaign_settings_snapshot`). When change
`ai-package-campaign-settings-snapshot` is applied, export MUST materialize the
**detailed** read-only campaign settings snapshot defined by
`ai-package-campaign-settings-snapshot` spec (`CampaignSettingsSnapshotV1`) for
in-scope shop inventory rows. Until that implementation lands, export MAY continue
minimal shop-scoped fields only: `AdvSetting` rows joined to `WBCabinet.shop_id`,
campaign identifiers, and Auto/Search id linkage per repo evidence.

Minimal-only export MUST NOT claim detailed field-level advertising settings
coverage. Detailed export MUST NOT treat this dataset as a **detailed** snapshot
without the dedicated domain contract, provenance, and leg model from change
`ai-package-campaign-settings-snapshot`.

Inclusion requires a proven read-only PG seam (`get_async_session_maker(read_only=True)`,
shop-scoped SELECT only, no WB writes, no `WBShopDataManager` orchestrator).
When the seam is not defensible at apply time, export MUST emit dataset-level
`UNKNOWN` or omit with explicit `reason_codes`, not fabricated inventory or
detailed settings rows. When included with partial discovery, `coverage` MUST
reflect **PARTIAL** inventory or **PARTIAL** detailed settings — not FULL WB
cabinet campaign universe.

#### Scenario: PG inventory is read-only minimal grain

- **GIVEN** PG inventory dataset is enabled per design
- **WHEN** export reads PG for shop S
- **THEN** only SELECT/read-only session patterns MUST be used
- **AND** `bot_active`, mode defaults, or WB write side effects MUST NOT occur
- **AND** rows MUST represent shop-scoped inventory/relations (not full
  detailed settings field export unless detailed snapshot change is applied)

#### Scenario: Detailed settings not implied by inventory card

- **GIVEN** v1 export for shop S without detailed snapshot implementation
- **WHEN** manifest describes `campaign_settings_snapshot`
- **THEN** export MUST NOT claim complete detailed advertising settings coverage
- **AND** absence of detailed settings MUST NOT be masked as FULL settings snapshot

#### Scenario: Detailed settings export uses dedicated contract when applied

- **GIVEN** change `ai-package-campaign-settings-snapshot` is implemented
- **WHEN** export materializes `campaign_settings_snapshot` for shop S
- **THEN** payload MUST conform to `CampaignSettingsSnapshotV1`
- **AND** manifest card MUST declare detailed settings export semantics
- **AND** Auto and Search legs MUST remain distinguishable in payload
- **AND** export MUST NOT serialize control-plane `CampaignResourceSnapshotV1` as the payload

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

### Requirement: Keyword performance datasets in ExportService

`ExportService` MUST integrate keyword performance datasets under logical prefix
`keyword_performance/` as part of the single AI Package export. A second exporter
MUST NOT be introduced.

#### Scenario: Keyword datasets in same manifest

- **GIVEN** keyword export enabled for shop S
- **WHEN** `ExportService.export` completes
- **THEN** manifest MUST list keyword dataset cards alongside existing v1 datasets
- **AND** MUST NOT require separate export invocation

#### Scenario: ExportService remains sole authority

- **WHEN** AI Package ZIP is produced for keyword feature
- **THEN** orchestration MUST flow through `ExportService`
- **AND** MUST NOT use standalone script as sole authority

### Requirement: DATA_MAP and coverage root files in manifest

Export MUST emit `DATA_MAP.json` and `coverage.json` as manifest payload files with
sha256 descriptors. Tampered DATA_MAP MUST fail validation.

#### Scenario: DATA_MAP in file descriptors

- **WHEN** export completes with keyword feature
- **THEN** manifest.files MUST include DATA_MAP.json sha256
- **AND** validator MUST verify hash on decode

### Requirement: Keyword history bounds documented vs ExportPeriod

Manifest `period` MUST continue describing caller bounds for legacy datasets.
Keyword datasets MUST document `all_available` bounds separately in DATA_MAP and
coverage metadata.

#### Scenario: Dual bounds documented

- **WHEN** DATA_MAP emitted
- **THEN** MUST contain `export_period_bounds` and `keyword_history_bounds` sections
- **AND** keyword_history_bounds MUST reflect CH MIN/MAX not ExportPeriod clip

### Requirement: Default keyword assembler in ExportService

`ExportService` MUST default-build `KeywordPerformanceAssembler` when the
constructor param is omitted — same pattern as `CampaignSettingsAssembler`
(`export_service.py:93-98`). Default export MUST include keyword datasets using
real read-only readers.

#### Scenario: Default export includes keyword datasets

- **GIVEN** production wiring constructs `ExportService()` without keyword params
- **WHEN** export completes for a shop with keyword history
- **THEN** manifest MUST list keyword dataset cards and payloads
- **AND** MUST NOT require optional feature flag opt-in

### Requirement: Constructor-injected keyword seams for tests

ExportService MUST accept optional constructor-injected keyword readers/assemblers
so unit tests use fake CH/Redis without live stores.

#### Scenario: Fake keyword reader in unit test

- **GIVEN** test injects fake `KeywordPerformanceAssembler`
- **WHEN** export runs
- **THEN** MUST NOT open real ClickHouse client for keyword path

### Requirement: Legacy export tests inject keyword fakes

Existing ExportService integration tests MUST inject explicit fake keyword
assemblers/readers to avoid live CH/Redis — same obligation as fake settings
assemblers today. Silent keyword omission is forbidden.

#### Scenario: Legacy integration test uses fake keyword assembler

- **GIVEN** test constructs ExportService with fake settings assembler (existing pattern)
- **WHEN** test also injects fake keyword assembler
- **THEN** export MUST produce existing dataset cards without error
- **AND** MUST NOT open live CH/Redis for keyword path

### Requirement: Full package ZIP via PackageZipAssembler

Operator full export MUST use `PackageZipAssembler` calling existing
`ExportService` and `encode_package`.

#### Scenario: ExportService remains sole dataset authority

- **WHEN** `PackageZipAssembler.assemble_zip` runs
- **THEN** all dataset payloads MUST originate from `ExportService.export`
- **AND** MUST NOT invoke a parallel exporter

### Requirement: Family gaps manifest file

Full ZIP MUST list `PACKAGE_FAMILY_GAPS.json` in manifest file descriptors
with deterministic content for identical export inputs.

#### Scenario: Gaps file hashed in manifest

- **WHEN** full ZIP is validated
- **THEN** `PACKAGE_FAMILY_GAPS.json` sha256 MUST match manifest entry

### Requirement: Analytical views are domain payloads

Экспорт полного пакета MUST прикладывать аналитический контракт, инструкцию чтения и витрины окон, посчитанные доменным слоем до кодирования архива. Эти документы MUST входить в манифест с контрольными суммами. Экспорт MUST NOT считать формулы внутри кодировщика архива.

#### Scenario: Manifest lists analysis contract

- **WHEN** полный пакет с аналитическим слоем собран
- **THEN** манифест MUST ссылаться на аналитический контракт и витрины окон
- **AND** подмена байтов контракта MUST ломать проверку пакета

### Requirement: Analysis read range follows windows

Чтение фактов для аналитических окон MUST покрывать номинальные границы этих окон до границы пакета и MUST NOT ограничиваться узким периодом вызывающей стороны, если источник хранит более длинную историю. Граница пакета MUST NOT объявляться полнотой источника. Период вызывающей стороны MUST оставаться отдельным полем. Ключевая история MUST по-прежнему не обрезаться этим периодом.

#### Scenario: Narrow caller period does not clip campaign analysis

- **GIVEN** вызывающий период короче 30 дней
- **AND** дневная статистика ноги хранится дольше 30 дней
- **WHEN** строится окно 30 дней
- **THEN** агрегат MUST использовать дни окна в пределах доступной истории
- **AND** MUST NOT ограничиться только вызывающим периодом

### Requirement: Package schema bump when analysis is present

Пакет, в котором есть аналитический слой, MUST объявлять схему пакета новее 1.0.0. Пакет без этого слоя MAY оставаться 1.0.0.

#### Scenario: Analysis package is not schema 1.0.0

- **WHEN** экспорт заявляет аналитические окна
- **THEN** версия схемы пакета MUST быть не ниже минора, вводящего этот слой
