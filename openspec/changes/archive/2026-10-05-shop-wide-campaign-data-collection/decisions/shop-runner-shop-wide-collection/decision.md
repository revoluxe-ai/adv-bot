# Decision: shop-runner — исполнение shop-wide сбора рекламных данных

## Status

Proposed

## Context

Change `shop-wide-campaign-data-collection` вводит сбор рекламных данных по всем
кампаниям подключённого магазина (включая кампании вне управления WB Sky).
Без явного placement rule возможны параллельные реализации: shop-runner в
prod-контуре магазина и отдельный collector в `scripts/` + Job runtime
(`/opsx-scripts`), что дублирует WB API access, расходует rate-limit и
расходится с Owner contract.

Owner в planning-чате этого change (2026-09-26) зафиксировал исполнителя:
**shop-runner**, не scripts/Job collector.

Owner revision (2026-09-26, `/opsx-update`): **временный dual-path** внутри
shop-runner — managed collection для кампаний под управлением WB Sky и
отдельный minimal read-only unmanaged path для остальных обнаруженных кампаний;
оба маршрута сосуществуют до погашения architectural debt
`openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md`.
Единый unified collector **не** утверждается этим decision.

## Decision

**TARGET / owner исполнения shop-wide сбора рекламных данных для этого change:**
контур **shop-runner** (per-shop runtime, существующий access plane и WB API stack
магазина).

**FORBIDDEN executor для этого change:** отдельное задание **scripts/Job collector**
(entrypoint в `scripts/`, исполнение в Owner-bot Job runtime `/opsx-scripts`) как
носитель shop-wide сбора рекламных данных по подключённому магазину.

**Temporary dual-path (Owner revision 2026-09-26):**

1. **MANAGED path** — существующий shop-runner collection для кампаний в **legacy RECORD collection ownership** (design §B.1: фактический universe `get_complex_advs` / `__get_advs`, incl. search legs и `refused` rows в loader'е); **MUST NOT** классифицировать route только по `bot_active`, только по «есть строка AdvSetting» или по connect UI predicate `NOT IN (done, refused)`.
2. **UNMANAGED path** — minimal read-only slice в том же shop-runner для WB-discovered кампаний **вне** §B.1 ownership set для **campaign advertising** grain `(adv_id, date)`; **MUST NOT** create `AdvSetting`,
   **MUST NOT** WB management writes, **MUST NOT** require `ComplexAdv`,
   **MUST NOT** вызывать целый `ClustersAdvStatUpdater` (KeywordSetting /
   ComplexAdv); initial slice **не** включает `clusters_adv_stats` (design §D.4);
   **MUST NOT** создавать independent `wb_common_stat` writer — shop-wide
   `(nmid, date)` owner **`shop-wide-common-sales-collection`** (legacy
   `CommonSaleStatUpdater` на managed loader остаётся под common-sales coordinator).
3. При connect/disconnect ownership сбора **переходит** между path; история
   `(shop_id, adv_id)` в CH **MUST** оставаться непрерывной (design §C).
4. **MUST NOT** автоматически расширять legacy `ComplexAdv` / `fact_stat_states`
   на все unconnected кампании в рамках этого change.
5. Architectural debt: `openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md`.

**Источник Owner:** ответ Owner «shop-runner» в planning-чате change
`shop-wide-campaign-data-collection`, 2026-09-26.

Инварианты change (не расширяются этим decision):

- Сбор не создаёт AdvSetting, не меняет `bot_active`, не подключает и не
  отключает кампании и не расширяет существующие write permissions.
- Доступные данные сохраняются в **существующих** хранилищах; partial success по
  правам токена (ошибка одного источника не останавливает остальные; причина
  недоступности фиксируется явно).
- «Все кампании» — обнаруживаемые через WB API, независимо от AdvSetting и
  `bot_active`; неизвестное состояние не трактуется молча как отсутствие.
- **Точный перечень статистики и collectors** в Owner contract не фиксируется;
  определяется в design после инвентаризации (decision не invent'ит каталог
  метрик).

**Связанные accepted constraints (цитировать, не противоречить):**

- `openspec/decisions/clickhouse-sql-database-qualification/decision.md` —
  application CH SQL MUST квалифицировать `default_db.<object>` в тексте запроса.
- `openspec/decisions/billing-fair-leg-metering-write-path/decision.md` —
  `bot_active` относится к billing/metering, **не** к фильтру universe сбора
  shop-wide RECORD data.
- `openspec/decisions/empty-keywords-pause-write-path/decision.md` и
  `openspec/decisions/auto-bid-module-coexistence-write-path/decision.md` (и
  родственные auto/pause write-path) — отдельные write-capabilities; **не**
  являются исполнителем shop-wide **сбора** рекламных данных этого change.
- `openspec/decisions/scripts-wb-api-ops-stack/decision.md` — применяется к
  операторским Job-скриптам в `scripts/`; **этот change не использует** тот
  executor для shop-wide сбора.

## Applies to

- Shop-wide сбор рекламных данных по всем кампаниям подключённого магазина в
  рамках change `shop-wide-campaign-data-collection`.
- Placement orchestration, scheduling и WB read-path вызовы, которые реализуют
  этот сбор в production-контуре магазина.
- Design/spec/tasks этого change при выборе runtime и write/read ownership.

## Allowed

- Реализация и запуск shop-wide сбора внутри shop-runner lifecycle (существующий
  per-shop worker, token plane, retry/rate-limit паттерны shop-runner).
- Запись доступных данных в существующие хранилища через application-owned
  read/write paths shop-runner (с учётом CH qualification и partial success).
- Design-инвентаризация конкретных источников статистики **без** расширения
  product scope Owner contract.

## Forbidden

- Shop-wide сбор рекламных данных по подключённому магазину как primary
  responsibility отдельного `scripts/` entrypoint + Job collector для этого
  change.
- Использование `/opsx-scripts` Job runtime как замены shop-runner для этого
  shop-wide сбора.
- Расширение сбора до AdvSetting create, изменения `bot_active`, connect/disconnect
  кампаний или расширения write permissions «ради полноты данных».
- Фильтрация universe сбора по `bot_active` как условие включения кампании в
  shop-wide RECORD (billing semantics остаются в billing decisions).

## Examples

**Good:** новый или расширенный шаг shop-runner загружает статистику по всем
обнаруженным кампаниям магазина и пишет в существующие stores; недоступный
endpoint логируется с явной причиной, остальные источники продолжают сбор.

**Bad:** cron Job `scripts/collect_shop_wide_adv.py` в Owner-bot runtime как
единственный или параллельный исполнитель того же shop-wide сбора для prod
магазина в рамках этого change.

**Bad:** исключить из universe кампании с `bot_active=false`, трактуя billing
флаг как gate сбора.

## Related specs

- Delta specs change `shop-wide-campaign-data-collection` (когда появятся) MUST
  ссылаться на этот placement; каталог статистики — после design inventory.

## Related changes

- `openspec/changes/shop-wide-campaign-data-collection` — источник proposed
  decision и Owner contract companion.

## Related architectural debt

- [`openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md`](../../../../architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md)

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing for shop-wide
      collection executor placement
- [ ] implementation layer matches decision (проверка на apply/verify)
