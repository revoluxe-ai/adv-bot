# ai-package-full-export Specification

## ADDED Requirements

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
