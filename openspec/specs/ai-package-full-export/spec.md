# ai-package-full-export Specification

## Purpose

Read-only operator surface: one shop, one ZIP, explicit gaps for dataset
families not yet in v1 export.

## Requirements

### Requirement: PackageZipAssembler is the ZIP authority

ZIP production MUST flow `ExportService` → optional family gaps payload →
`encode_package`. A second exporter MUST NOT be introduced.

#### Scenario: Single orchestration path

- **WHEN** full package ZIP is built
- **THEN** `ExportService` MUST run first for domain payloads
- **AND** `PackageZipAssembler` MUST NOT duplicate dataset readers

### Requirement: PACKAGE_FAMILY_GAPS.json

Full ZIP MUST include root `PACKAGE_FAMILY_GAPS.json` listing families with
`status: GAP` and `reason_codes` for families not materialized in v1 export
(campaign settings history, supplier shop orders/sales feed, store DRR,
prices/stocks, finance, discovery).

#### Scenario: Explicit gap not silent success

- **WHEN** a family is absent from export payloads
- **THEN** gaps file MUST name the family with GAP status
- **AND** MUST NOT imply FULL coverage for that family

### Requirement: One shop one ZIP

CLI and assembler MUST accept exactly one `shop_id` per invocation.

#### Scenario: Shop isolation preserved

- **WHEN** export runs for shop S
- **THEN** manifest `shop_id` MUST reference only S

### Requirement: Assembler does not own analysis formulas

Полный ZIP MUST по-прежнему собираться одним кодировщиком после доменного экспорта. Кодировщик MUST NOT заново агрегировать сырые ряды по окнам и MUST NOT вводить второй экспортёр.

#### Scenario: Single encode path with analysis files

- **WHEN** полный пакет включает аналитические витрины
- **THEN** витрины MUST уже быть доменными payload
- **AND** кодировщик MUST NOT создавать вторую копию ключевых окон под другим именем

### Requirement: Existing gap families stay honest

Появление аналитических окон MUST NOT переводить семейства разрыва в полный статус. Разрыв выручки магазина, истории настроек, событий изменений и DRR магазина MUST оставаться разрывом, пока отдельный источник их не закроет.

#### Scenario: Windows do not close store DRR gap

- **GIVEN** семейство DRR магазина отсутствует в источниках пакета
- **WHEN** аналитические окна добавлены
- **THEN** каталог разрывов MUST по-прежнему называть это семейство разрывом
