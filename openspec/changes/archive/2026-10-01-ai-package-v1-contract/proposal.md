## Why

После Accepted стратегии источников (`shop-data-source-strategy`) и синхронизированных
capability-спеков нужен **следующий независимый implementation change**: bounded
read-only экспортёр AI Package v1, который по `shop_id` и ограниченному периоду
собирает versioned ZIP с manifest и `sha256`, читая **только** уже накопленные
PostgreSQL и ClickHouse — без WB API, без новых collectors и без расширения
стратегии накопления.

## What Changes

- **Intent:** зафиксировать доменный контракт пакета (datasets, зерно, provenance,
  scope/capabilities/access, четыре измерения полноты) и отдельно транспорт ZIP;
  спланировать read-only экспортёр с детерминированным manifest и контрактными
  тестами.
- Вход: `shop_id` + bounded `[period_start, period_end]` (включительно, семантика
  дат — в design/spec).
- Выход: versioned ZIP + manifest (per-file `sha256`, schema version, shop scope).
- Источники v1 (read path):
  - campaign full stat — ClickHouse `default_db.full_adv_wb_stat`, зерно
    `campaign_id` + `date`;
  - common/funnel — ClickHouse `default_db.wb_common_stat` **только** для
    `nmid` основного товара каждого `ComplexAdv` магазина, **не** shop-wide
    product order feed;
  - PG **inventory / relations** (shop-scoped `AdvSetting` + `WBCabinet.shop_id`,
    Auto/Search id linkage) — read-only, explicit `PARTIAL`/`UNKNOWN`; **не**
    детальный snapshot настроек РК (вне v1 — см. Out of scope).
- Product shop orders/sales: **SOURCE_NOT_ASSIGNED** / `UNKNOWN` в manifest и
  dataset cards — без подмены funnel/ad orders или supplier GET.
- `collection_outcome`, `coverage`, `reason_codes`, `freshness` — независимые поля;
  `NO_DATA` ≠ автоматически incomplete coverage; `UNKNOWN` fail-closed; отсутствие
  источника ≠ silent success.
- Контрактные тесты (tests-first): ZIP без WB call; absent source → `UNKNOWN`;
  empty data ≠ full coverage; Auto/Search `campaign_id` разделены; `sha256`
  детерминизм; shop isolation.
- Первый вертикальный slice и quality gates — в `tasks.md` (без `/opsx-apply` в
  этом hop).

### Scope (in)

- OpenSpec artifacts: proposal, specs, design, proposed decision (placement),
  `owner-contract.md`, scenario-coverage plan, tasks.
- Domain contract независим от ZIP; ZIP — transport layer.

### Out of scope (explicit)

- `shop-wide-campaign-data-collection` (discovery вне инвентаря).
- Collectors, backfill, CSV poller, DDL/миграции CH/PG, prod campaign writes.
- GUI, Telegram UI, AI response JSON, preview/apply.
- Sibling worktrees; change `inc-ro-08-orders-sales-period-collect`.
- Detailed advertising campaign **settings** snapshot export (candidate future
  change `ai-package-campaign-settings-snapshot`).
- Живой WB API из экспортёра; `WBShopDataManager` / min-bids backfill on export
  path; fabricated numeric WB limits; fake coverage from timestamps; implicit
  full history or full WB campaign universe from PG inventory alone.
- Реализация product code в этом invocation.

### Current Behavior

Стратегия источников Accepted и четыре canonical specs синхронизированы в
`openspec/specs/`, но **нет** change с форматом пакета, manifest/ZIP контрактом
и placement read-only экспортёра в текущем worktree.

### Desired Behavior

Оператор/Job может (после apply отдельного hop) построить AI Package v1 ZIP из
накопленных PG/CH с честными coverage/reason_codes и без side-effect writes;
validator и contract tests воспроизводимо доказывают read-only и семантику
источников.

### Risk

- Неверный scope funnel (`wb_common_stat` на весь shop) → ложная «товарная»
  аналитика; mitigation — spec + negative tests.
- Подмена shop orders funnel/ad полями → violation
  `orders-or-sales-reports-read-identity` / shop strategy; mitigation — explicit
  `SOURCE_NOT_ASSIGNED`.
- CH SQL без `default_db` qualification → violation
  `clickhouse-sql-database-qualification`; mitigation — design placement on
  existing qualified queries or new SQL with qualification.

### Rollback idea

Planning-only: удалить/не merge change `ai-package-v1-contract`. Post-apply:
отключить entrypoint Job/script экспортёра; ZIP generation off by flag — без
отката данных PG/CH.

## Capabilities

### New Capabilities

- `ai-package-v1-exporter`: доменный контракт datasets, scope/access, coverage
  dimensions, read paths PG/CH, manifest semantics, bounded period export.
- `ai-package-v1-contract-tests`: deterministic validator, contract tests
  (no WB, UNKNOWN sources, grain separation, sha256, shop isolation).

### Modified Capabilities

_(пусто — canonical strategy specs уже в main; этот change не меняет их
REQUIREMENTS, только потребляет.)_

## Impact

- Будущий код: новый read-only модуль/Job под `app/` (точный path — design),
  re-use паттернов `full_wb_adv_stat`, `common_stat_manager` / shop PG load.
- ClickHouse qualified reads `default_db.*`; PostgreSQL read-only sessions.
- Tests: unit contract tests + targeted integration с test CH/PG fixtures.
- Не затрагивает shop-runner write path, collectors, billing, TG handlers.
