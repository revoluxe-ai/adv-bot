## Why

Настройки рекламной кампании WB Sky сейчас распределены по нескольким PostgreSQL settings-сущностям, а Excel использует вручную поддерживаемые whitelist-наборы полей. Из-за этого новое или переименованное поле может появиться в production, но не попасть в историю настроек или Excel-представление, и такой пропуск обнаруживается только вручную.

Нужен единый versioned contract настроек кампании, из которого строится change-only history и контролируется Excel projection. Добавление или изменение settings-поля без явной классификации MUST fail closed на contract test, а не молча выпадать из истории.

## Intent

Ввести канонический контракт настроек рекламной кампании и долговечную историю его изменений, сохранив Excel human-facing представлением того же контракта.

## Current behavior

- Настройки кампании находятся не в одной таблице: как минимум AdvSetting, KeywordSetting, AutoShelfBidControlSettings, AdvTimeSettings и AdvTimeWeekMask.
- Excel export/import отдельно поддерживает ручные наборы editable/read-only полей.
- История полного канонического состояния настроек по времени отсутствует.
- Наличие ORM-колонки само по себе не определяет, является ли она пользовательской настройкой, runtime-state или WB-synchronized fact.
- При добавлении нового settings-поля нет обязательного механизма, который заставляет разработчика определить его history/Excel policy.

## Desired behavior

- Для каждой кампании существует canonical normalized settings payload с versioned schema.
- Поля settings-owned sources имеют явную classification policy: history include/exclude и Excel editable/read-only/excluded.
- Любое новое, удалённое или переименованное поле в settings-owned source без обновлённой classification policy MUST ломать deterministic contract test.
- History сохраняет snapshot только когда canonical state_hash изменился; одинаковое состояние не дублируется.
- Сбор истории запускается периодически, ориентир — раз в 5 минут, и не зависит от UI/Excel.
- Excel остаётся human-facing projection того же canonical contract; он не становится отдельным source of truth.
- Unknown/unsupported field classification MUST fail closed.

## What Changes

- Добавляется capability campaign-settings-history с canonical settings contract, schema_version и deterministic normalization/hash.
- Добавляется обязательный field registry/classification для settings-owned sources.
- Добавляется change-only storage истории настроек в ClickHouse с миграцией через принятый ClickHouse migration control plane.
- Добавляется периодический collector, который читает PostgreSQL settings state и пишет только новый hash.
- Excel schema/projection переводится на тот же field registry либо покрывается parity contract, исключающий ручной drift.
- Добавляются contract/regression tests, которые падают при появлении settings-поля без history/Excel policy.

## Scope In

- AdvSetting settings-поля.
- KeywordSetting поля, которые являются управляемой конфигурацией ключа.
- AutoShelfBidControlSettings.
- AdvTimeSettings и AdvTimeWeekMask.
- Явная classification существующих полей этих settings-owned sources.
- Canonical serialization/normalization, schema_version, state_hash.
- Change-only history и read/query contract истории.
- Excel projection/parity относительно canonical field registry.
- ClickHouse DDL для history через versioned migration control plane.

## Scope Out

- Фактическое физическое состояние кампании в WB как canonical settings source.
- Plan/fact, продажи, расходы, статистика, remaining budget и performance metrics.
- Runtime decision state, transient locks/latches, diagnostic state и operational traces, если они не являются пользовательской настройкой.
- Изменение рекламной логики, ставок, bidder/V3 decision rules.
- Новое AI/API/MCP управление настройками; этот change только создаёт canonical contract/history foundation.
- Редизайн Telegram UI.
- Перенос PostgreSQL settings authority в ClickHouse.

## Capabilities

### New Capabilities
- `campaign-settings-history`: versioned canonical campaign settings contract, fail-closed field classification, change-only history и Excel projection parity.

### Modified Capabilities
- `clickhouse-migration-lifecycle`: reviewed migration `006` для settings-history становится частью canonical corpus; `005` остаётся privileged GRANT, schema-writer расширяется только на reviewed schema DDL `006`, без ослабления fail-closed правил.

## Impact

Затрагиваются PostgreSQL settings models и их metadata/classification, Excel export/import schema, новый history collector, ClickHouse history schema и тестовый contract coverage. PostgreSQL остаётся authority текущих настроек; ClickHouse хранит append-only исторические snapshots.

## Risk

Главный риск — неверно включить runtime/WB-state в canonical settings или, наоборот, пропустить реальную настройку. Поэтому inclusion не выводится только по типу ORM-колонки: каждое candidate field обязано иметь явную policy, а unknown classification блокирует validation.

Второй риск — расхождение Excel и history. Оно устраняется единым registry/parity test, а не синхронизацией двух ручных списков.

## Rollback idea

Collector и запись history можно отключить без изменения текущего PostgreSQL authority и рекламных write-path. Новая ClickHouse history таблица остаётся read-only историческим артефактом. Excel projection может быть возвращена на предыдущий renderer/importer, но canonical field registry и coverage test не должны удаляться без отдельного architecture change.
