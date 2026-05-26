# Auto Shelf Bid Control v1

Контур управляет общей ставкой полок Auto-РК для single-nmid кампаний.

## Единицы ставок (обязательно)

| Слой | Единица | Примечание |
|------|---------|------------|
| PG `*_minor`, CH `bid_minor`, Redis recommendations, setter | **копейки** | 200 ₽ → `20000` |
| Redis / `AdvMinNmidsBids` min bids | **рубли** (legacy CPM) | Конвертация в control: `×100` (`bid_units.wb_min_cpm_rub_to_bid_minor`) |
| Telegram ввод max / шаг | **рубли** | Сохранение: `rubles_to_bid_minor` |
| Telegram отображение | **рубли** | `format_bid_minor_for_telegram` (`/100`) |

Модуль контракта: [`bid_units.py`](bid_units.py).

**Минимальная ставка WB** — только из кэша `min_bids` (не из CH, не из текущей ставки).

### Тест vs main (семантика)

- **Покрытые ставки / CPA по ставке** — агрегат по `bid_minor` без фильтра `mode`
  (test+main на одной ставке — одна строка), окно цикла от `current_cycle_started_at`.
- **Порог test-фазы** — прогресс `target_test_impressions` с `test_started_at`
  (fallback: `current_cycle_started_at`), по `bid_minor` текущего test без фильтра mode.
- **Порог main-фазы** — прогресс main: `mode=main`, `current_main_bid_minor`,
  `from_ts=main_started_at` (только сегмент main на main-ставке).

### Legacy repair (без миграции PG)

Если в settings остались старые значения (`max_bid_minor=500` как «5 ₽», шаг `1` как «0.01 ₽»),
при открытии Telegram-экрана и на каждом тике `AutoShelfBidControlManager.update` вызывается
[`settings_normalizer.py`](settings_normalizer.py): `max` и шаг приводятся к копейкам, test-ставка
в state выравнивается в диапазон `[min_wb, max]` (обычно до текущей WB-ставки).

## Ключевые принципы

1. Корутина `auto_shelf_bid_control` вызывает `update` только для
   `AutoShelfBidControlManager.is_coroutine_candidate` (не для всех РК магазина).
2. Кандидаты `update` с фильтрами:
   - `bot_active == True`
   - `auto_adv_active_status == True`
   - `adv_setting.auto_shelf_bid_control_enabled == True`
   - `len(nmids) == 1`
   - задан `auto_adv_id`
3. Фактическая ставка читается только из Redis-кэша
   `RedisAutoRecommendationsBidValueManager` (`auto_adv_id + nmid`).
4. Аналитика читается из `auto_shelf_bid_intervals` с обязательным read-time dedup:
   `GROUP BY event_date,event_id + argMax(..., version)`.
5. Переходы `test <-> main` основаны на порогах показов.
6. `best_bid` для main — **глобальная**: min CPA ``spend/greatest(carts,1)`` среди лучших
   цикла (`resolve_cycle_best_bids`, предыдущий — окно `[prev, current)`). Fallback:
   отчётный день → текущий main → actual → middle. В main-фазе ставка
   синхронизируется с глобальной на каждом тике.
   затем fallbacks. Итоговая main-ставка ограничивается `[min_bid_minor, max_bid_minor]`
   (`_clamp_bid_minor`). Смена фазы test↔main: `save_state` до PATCH WB
   (`_persist_state_then_set_bid`).
7. `next_test_bid` выбирается как максимально удаленная непокрытая точка диапазона
   `[min_bid_minor, max_bid_minor]` (оба в копейках).
8. `get_bid_stats` / best bid по CPA: одна строка на `bid_minor` (mode в CH не дробит точку).
9. Telegram: на главном экране блока «Покрытые ставки» нет. Кнопка «Покрытия цикла» —
   до `TELEGRAM_BID_POINTS_VIEWER_PAGE_SIZE` (10) строк: все ставки с показами в цикле,
   сортировка по CPA (лучшие сверху), ✅ покрыта / ⏳ набор / ⭐ лучшая глобальная.
   Агрегаты по `bid_minor` от `current_cycle_started_at`, ◀️/▶️. «Лучшая ставка цикла»
   в UI — «Лучшая ставка цикла» (`cycle_best`) и «Лучшая глобальная ставка»
   (`global_best` = min CPA текущий ∪ предыдущий цикл). `next_test_bid` /
   `covered_points_count` — отчётный день.

## Conversion policy v1 (setter)

`bid_minor` (копейки) → WB `PATCH /api/advert/v1/bids` как `bid_kopecks` (без ×100).
После PATCH `AutoShelfBidSetter` пишет ту же ставку в
`RedisAutoRecommendationsBidValueManager` (control/UI читают actual bid из Redis).
Legacy `adv/v0/bids` не используется (404 на WB).

Подтверждение перед прод: `AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED` и gate в UI.

## Dry-run

Источник dry-run только один:

1. env `AUTO_SHELF_BID_CONTROL_DRY_RUN`

Если значение `true`, setter работает в безопасном режиме без PATCH в WB API.

## Integration

- Корутина: `CoroutinesManager.auto_shelf_bid_control()`.
- Режим для инкремента: `AutoShelfBidRepository.get_current_mode()` берет mode
  из `AutoShelfBidControlState` при включенном control-флаге, иначе `main`.
