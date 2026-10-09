# ai-package-v1-contract-tests Specification

## ADDED Requirements

### Requirement: Contract tests for window semantics

Контрактные проверки MUST покрывать номинальные границы окон, агрегаты 1, 3, 7, 14, 30, 90, 180 и 365 дней, идентичность ног Auto и Search и охват пакета отдельно от расхода всего магазина. Проверки MUST NOT требовать записи в WB.

#### Scenario: Tampered analysis contract fails validation

- **GIVEN** пакет с аналитическим контрактом
- **WHEN** байты контракта изменены после сборки
- **THEN** проверка пакета MUST завершиться неуспехом

### Requirement: Contract tests for fail-closed economics

Проверки MUST покрывать изоляцию прямой и связанной областей, несопоставимое сравнение, версии пакета и контракта и одинаковый доменный результат на шве транспорта.

#### Scenario: Uncomputable economics are not numeric

- **GIVEN** нет фактов атрибуции и нет выручки магазина
- **WHEN** проверка читает окно ноги и агрегат охвата пакета
- **THEN** прямые и связанные экономические метрики и DRR магазина MUST быть невычислимы
- **AND** расход всего магазина MUST быть невычислим
- **AND** MUST NOT быть числом ноль
