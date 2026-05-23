# Auto Shelf Bid Increment Manager (v1)

Краткий decision log по текущей реализации инкрементов для полок Auto-кампаний.

## Decision Log

1. **Строгая атрибуция важнее полноты boundary-дельт**
   - При смене контекста (`bid_minor`, `currency`, `mode`, `price_*`) интервал не пишется.
   - Выполняется только `persist(current_snapshot)` (`context_changed_resync`), чтобы не смешивать метрики разных сегментов.

2. **`recommendations_stat = total_auto - keyword` — единственная формула v1**
   - Если `keyword_stat` отсутствует, используется `zero` с событием `keyword_stat_missing_use_zero`.
   - Если результат отрицательный, интервал не пишется (`negative_recommendations_skipped`).

3. **После negative-фазы используется `resync_required`**
   - На отрицательной фазе ставится Redis-маркер `resync:auto_shelf_bid:{nmid}`.
   - Первый следующий валидный тик только выравнивает `prev` (`negative_recommendations_resync`) без записи интервала.

4. **Отрицательные и нулевые дельты не попадают в intervals**
   - `negative_delta_skipped` -> `persist` без insert.
   - `zero_delta_skipped` -> `persist` без insert.
   - Пишутся только валидные положительные дельты (`insert_ok`).

5. **Цена в v1 намеренно отключена**
   - `price_minor` всегда `NULL` (`price_currency='RUB'`).
   - Поток не зависит от внешнего источника цены; это осознанный компромисс текущей итерации.

6. **Single-NMID guard обязателен**
   - Кампании без `nmid` или с несколькими `nmid` в v1 пропускаются:
     `single_nmid_guard_empty` / `single_nmid_guard_multiple`.

7. **`prev` хранится в Redis + ClickHouse**
   - Чтение: сначала Redis, затем fallback в CH.
   - Запись: Redis и CH одновременно для устойчивости к рестартам.

8. **Дедуп-контракт по `event_id` (write + read)**
   - Write-time: insert в `auto_shelf_bid_intervals` идемпотентен по `(event_date, event_id)`.
   - Read-time: аналитические SQL по intervals должны дедупить через
     `GROUP BY event_date, event_id` + `argMax(..., version)`.
   - Даже если физдубль строки появился из-за partial-failure, аналитические суммы
     не должны задваиваться.

## Основные события в логах

- `insert_ok` — успешная запись интервала.
- `context_changed_resync` — смена контекста, только resync.
- `negative_recommendations_skipped` — отрицательный `recommendations`, интервал пропущен.
- `negative_recommendations_resync` — первый валидный тик после negative-фазы, только resync.
- `negative_delta_skipped` / `zero_delta_skipped` — дельта невалидна для insert.
- `persist_failed_after_interval` — interval вставлен, но persist prev не удался.

## Что считать корректным поведением

- Возможны тики без записи интервала — это ожидаемо в resync/guard ветках.
- Пропуск "пограничной" дельты при смене контекста — намеренное поведение для строгой атрибуции.
- Отсутствие цены (`price_minor=NULL`) в v1 — нормальный сценарий.
- При `persist_failed_after_interval` допускается окно частичного сбоя; корректность
  аналитики обеспечивается дедупом по `event_date + event_id`.
