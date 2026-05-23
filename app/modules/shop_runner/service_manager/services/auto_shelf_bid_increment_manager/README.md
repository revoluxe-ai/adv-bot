# Auto Shelf Bid Increment Manager (v1)

Краткий decision log по текущей реализации инкрементов для полок Auto-кампаний.

## Decision Log

1. **Строгая атрибуция важнее полноты boundary-дельт**
   - При смене контекста (`bid_minor`, `currency`, `mode`, `price_*`) интервал не пишется.
   - Выполняется только `persist(current_snapshot)` (`context_changed_resync`), чтобы не смешивать метрики разных сегментов.

2. **`recommendations_stat = total_auto - keyword` — единственная формула v1**
   - Если `keyword_stat` отсутствует (`None`), тик пропускается с ошибкой
     `keyword_stat_missing_skip` (без insert и без persist).
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

9. **Каденс корутины и bucket различаются**
   - Корутина может запускаться примерно раз в 5 минут.
   - `bucket_start` и lock-сетка считаются по 15-минутной сетке (общий `BucketCalculator`).
   - Это согласовано с референсом incremental-пайплайна и общими утилитами.

## Основные события в логах

- `insert_ok` — успешная запись интервала.
- `context_changed_resync` — смена контекста, только resync.
- `negative_recommendations_skipped` — отрицательный `recommendations`, интервал пропущен.
- `keyword_stat_missing_skip` — `keyword_stat` недоступен, тик пропущен с `ERROR`.
- `negative_recommendations_resync` — первый валидный тик после negative-фазы, только resync.
- `negative_delta_skipped` / `zero_delta_skipped` — дельта невалидна для insert.
- `persist_failed_after_interval` — interval вставлен, но persist prev не удался.

## Что считать корректным поведением

- Возможны тики без записи интервала — это ожидаемо в resync/guard ветках.
- Пропуск "пограничной" дельты при смене контекста — намеренное поведение для строгой атрибуции.
- Отсутствие цены (`price_minor=NULL`) в v1 — нормальный сценарий.
- При `persist_failed_after_interval` допускается окно частичного сбоя; корректность
  аналитики обеспечивается дедупом по `event_date + event_id`.

## Failure window (insert -> persist)

- В success-path порядок операций: `insert_interval` -> `persist(prev)`.
- Если `insert_interval` успешен, а `persist(prev)` падает, фиксируется
  `persist_failed_after_interval` и выставляется `resync_required`.
- Повторный тик с тем же `event_id` не должен задваивать аналитику благодаря
  write-time idempotent insert и read-time дедупу по `event_date + event_id`.

## Для ревью: частые вопросы (намеренные решения, не баги)

Ниже — ответы на типичные замечания code review. Если пункт совпадает с
наблюдаемым поведением в коде/логах, это **ожидаемый контракт v1**, а не
регрессия.

### 1. «При смене bid/mode/price теряется boundary-дельта»

**Ответ:** да, намеренно. При `context_changed_resync` interval не пишется,
обновляется только `prev`. Мотивация — строгая атрибуция: дельта между двумя
разными сегментами (например, до и после смены ставки) не должна попасть в
интервал нового сегмента. Полнота boundary-интервалов сознательно жертвуется
ради корректной сегментации. См. decision log п.1 и `_is_context_changed()`.

### 2. «В repository нет fetch цены — dead code / недоделка?»

**Ответ:** нет. В v1 `price_minor` всегда `NULL`, задаётся в
`AutoShelfBidIncrementManager.update()` (блок «Цена (v1)»). Методы fetch price
удалены намеренно: нет надёжного runtime-источника, сегментация по цене — v2.
Колонки `price_*` в CH и проверки в validate SQL оставлены для forward-compat.

### 3. «Корутина ~5 мин, а bucket 15 мин — рассинхрон?»

**Ответ:** нет. Используется общий `BucketCalculator` (15 мин), как в
`increment_fact_data_manager`. Частые тики попадают в один bucket; lock на
`(shop, nmid, bucket_start)` предотвращает дубли записи внутри bucket.
Документация и комментарии в `update()` явно фиксируют эту модель.

### 4. «Сначала insert interval, потом persist prev — риск double-count?»

**Ответ:** риск осознан и закрыт двумя слоями:
- write-time: `insert_auto_shelf_bid_interval.sql` — `WHERE NOT EXISTS` по
  `(event_date, event_id)`;
- read-time: аналитические SQL — `GROUP BY event_date, event_id` +
  `argMax(..., version)` (см. `sum_auto_shelf_bid_interval_deltas_dedup.sql`).
При сбое persist после insert — `persist_failed_after_interval` +
`resync_required`; следующий тик не должен задвоить сумму в аналитике.

### 5. «Negative recommendations — почему не persist prev?»

**Ответ:** отрицательный `total_auto - keyword` трактуется как шум/рассинхрон
источников, а не валидное состояние для delta. Snapshot в prev не пишется;
ставится только `resync_required`. Первый следующий валидный тик выполняет
`negative_recommendations_resync` (persist без interval), затем pipeline
продолжается в штатном режиме.

### 6. «Negative delta — почему persist, но без insert?»

**Ответ:** отрицательная дельта между двумя валидными snapshot считается
аномалией метрик (сброс/лаги CH). Мы обновляем `prev` до текущего состояния,
чтобы не тащить некорректную базу в следующий тик, но interval не пишем
(`negative_delta_skipped`).

### 7. «Все price_minor в CH NULL — баг?»

**Ответ:** нет, норма v1. См. п.2 и decision log п.5.

### Карта reason -> что произошло

| reason | interval | prev | комментарий |
|--------|----------|------|-------------|
| `prev_missing_initialized` | нет | да | первый тик, база для delta |
| `negative_recommendations_skipped` | нет | нет | только resync-маркер |
| `keyword_stat_missing_skip` | нет | нет | нет данных keyword, безопасный skip |
| `negative_recommendations_resync` | нет | да | выравнивание после bad phase |
| `context_changed_resync` | нет | да | смена сегмента, без boundary delta |
| `negative_delta_skipped` | нет | да | аномальная delta |
| `zero_delta_skipped` | нет | да | нет изменений метрик |
| `insert_ok` | да | да | штатный success-path |
| `persist_failed_after_interval` | да* | нет | *interval уже в CH; resync на след. тике |
