# Owner Contract

## Что хотим получить

Shop-runner на каждом тике собирает фактическую воронку/common-sales по **всем текущим не-trash SKU магазина** за скользящие 7 календарных дней MSK (включая сегодня как provisional) и пишет их в существующую таблицу `wb_common_stat`. Legacy-сбор по nmID рекламных кампаний сохраняется; shop-wide координатор покрывает только непересекающуюся часть ассортимента.

## Зачем

Сейчас common-sales собираются только по `main_nmid` активных ComplexAdv. Не-рекламные и вне-кампанийные SKU не попадают в `wb_common_stat`, из-за чего shop-wide метрики и downstream read-only аналитика неполны. Нужен честный runtime MVP без отдельного процесса и без подмены кампанийного inventory.

## Что должно остаться неизменным

- Существующий WB funnel adapter, batching по 20 nmID, DTO-нормализация и writer в `wb_common_stat` (ReplacingMergeTree, version).
- Эксклюзивная ownership граница: common-sale coordinator — `(nmid, date)` shop-wide; sibling campaign change — discovery/inventory/advertising `full_adv_wb_stat`.
- Missing/null/partial **никогда** не превращаются в ноль; при сбое старые факты и freshness остаются правдивыми.
- Глобальная политика `NotFoundActiveAdvCompany` → `StopShopUpdateException` для прочих корутин не ослабляется.
- Нет WB advertising writes, создания AdvSetting, мутаций `bot_active`, независимых scripts/Job executor, второго процесса, campaign funnel route.
- Numerator для Store DRR остаётся `BLOCKED_BY_CAMPAIGN_COVERAGE`; не заявляем полный Store DRR.

## Чего сейчас не делаем

- Backfill истории старше 7 MSK-дней (`HISTORY_BACKFILL=DEFERRED`).
- Фейковая дневная история из period aggregate.
- Новая common-facts таблица; repurposing `SHOP_PRODUCT_ORDERS_SALES`.
- Копирование dirty AI Package exporter целиком; dirty stage не трогаем.
- AdvSetting / ComplexAdv / sold IDs / WBCard cabinet cache как authority all-shop assortment (WBCard loader без cabinet FK).
- Control-plane / transport scope; canonical spec/index promotion.

## Как поймём, что получилось

- На тике логируются без секретов: `shop_id`, `all_shop_nmids_count`, `existing_covered_count`, `uncovered_count`, `updated_count`, `failed_count`, `coverage_status`.
- Для магазина с |A|=500, |E|=120, |U|=380: множества disjoint, без duplicate nmID в collect input.
- Переходы non-ad→ad и ad→non-ad пересчитываются каждый тик; исторические строки CH не удаляются.
- Assigned E включает nmID, отсутствующие в текущем A; coverage universe для full-shop отдельно квалифицирует текущий A.
- Acceptance matrix (unit + integration) проходит по сценариям из delta spec; planning review — независимо.

## Решения Owner

- Runtime MVP расширяет factual funnel/common-sales через существующий adapter/collector/CH writer на все current shop SKU.
- Universe A: current non-trash cards через `ProductsManager.get_cards_list` (Content API pagination); fail-explicit при null/partial pagination.
- E: freeze legacy-assigned nmIDs из `main_nmid` snapshot ComplexAdv с `only_bot_active=False`; U=A−E disjoint; E — assigned input, не success set.
- Один coordinator в shop-runner; тот же shared adapter, batch 20, limit/retry state, DTO, writer.
- Campaign sibling owns `full_adv_wb_stat` only; reconciliation dependency явна, если sibling ещё не сведён.
- No-campaign: bounded seam — изолировать missing-ad source к E=∅ без отмены TaskGroup shop-wide path.
- Coverage read: minimal latest per `(nmid, date)` через argMax-семантику (как `wb_common_stat_period_totals`); row_count ≠ completeness.
- Source currency и money handling — как существующие метрики API→DTO→CH; без unsupported RUB assertion.
