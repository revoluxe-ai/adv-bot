## Context

Продукт переходит к freemium: один backend, в перспективе один Telegram-бот с переключением paid/free через `AdvSetting.bot_active` (сейчас — «бот включён на кампании» = paid automation). Параллельно free UI будет тестироваться на отдельном боте, paid UI остаётся без изменений.

Сегодня `bot_active` — единый gate в `WBShopDataManager._get_active_advs()`: при `False` кампания не попадает в `get_complex_advs()` и выпадает из **всех** корутин shop-runner, включая запись статистики и keyword stamps. Это противоречит целевой модели free: **запись всегда**, **мутации WB только при paid**.

В коде ACT-фильтры дублируются: часть корутин снова фильтрует `bot_active` после `get_complex_advs()`; `auto_shelf_bid_control` проверяет `bot_active` только внутри `_is_eligible`. Billing и pricer уже считают только `bot_active=True` кампании.

Этот change **не меняет production-код** — только тесты, маркеры, README и матрицу корутин. Рефакторинг data loader — отдельный follow-up change.

## Goals / Non-Goals

**Goals:**

- Два изолированных pytest-набора с явными маркерами и папками.
- Контрактные unit-тесты на уровне `CoroutinesManager` / managers: мок WB modifier/setter, assert not called при `bot_active=False`.
- Paid regression: inverse-тесты и curated list существующих billing/UI тестов.
- Документированная матрица ACT vs RECORD для всех корутин из `WBShop.run()`.
- Команды запуска для pre-merge проверки free-веток.

**Non-Goals:**

- Реализация free UI, второго бота, env-флагов tier.
- Изменение `_get_active_advs()` и snapshot updater filter в этом change.
- E2E через реальный Telegram.
- Полное покрытие всех 40+ client_bot handlers (только P0 paid path).

## Decisions

### 1. Два каталога + два маркера (не один смешанный suite)

**Решение:** `tests/paid_regression/` + `@pytest.mark.paid_regression`; `tests/bot_active_gates/` + `@pytest.mark.bot_active_gates`.

**Почему:** разные intent и lifecycle — paid suite всегда GREEN; gate suite на RECORD может быть `xfail` до рефакторинга loader.

**Альтернатива:** один каталог с двумя маркерами — отвергнута: хуже discoverability для команды («прогони paid»).

### 2. Unit-тесты с моками на уровне coroutine entrypoint

**Решение:** патчить `get_complex_advs` → возвращать один `ComplexAdv` с нужным `bot_active` и **включёнными** auto-flags; патчить WB write dependencies (`wb_modifier`, `_set_target_bid`, `update_cluster_bids`, whitelist updaters).

**Почему:** быстро, без Docker, стабильно в CI; ловит утечки gate при включённых флагах.

**Детали реализации (выявлены при apply):**

- Патчить **модуль-источник** lazy import (например `app.modules.shop_runner...CommonSaleStatUpdaterContainer`), а не имя в `manager.py` — иначе mock не срабатывает.
- `WBApi` в conftest собирать через корневую фикстуру `access_mock` (токены WB), не голый `MagicMock`.
- Для одного тика корутины — `unwrap_coroutine()` снимает `while_coroutine_decorator`.
- `auto_shelf_bid_control`: корутина всегда вызывает `run_tasks`; gate проверяется по **пустому** списку handlers или отсутствию WB setter в handler.
- `update_common_bid_in_search_adv`: не стабить `get_wb_advs_dto` в `[]` для inactive gate. Тест должен вернуть непустой DTO/search input и настроить resolver так, чтобы при отсутствии `bot_active` gate код дошёл бы до `UpdateCommotBidInSearchAdvsManager.update_common_bid_in_search_adv`; иначе `assert_not_called()` проверяет только ранний выход по пустым данным.

**Альтернатива:** integration с реальным Redis/CH — отложена на P1 для RECORD path.

### 3. `is_paid_actions_enabled(adv) -> adv.bot_active` как будущий helper (только в тестах сейчас)

**Решение:** в conftest gate-suite ввести функцию-контракт (можно дублировать логику `bot_active`); в follow-up change вынести в `app/modules/shop_runner/access.py`.

**Почему:** единая точка для смены семантики, если появится поле `tier`.

### 4. RECORD gate-тесты — `xfail(strict=False)` с reason до рефакторинга loader

**Решение:** тесты `test_recording_still_runs_when_bot_inactive` помечать `xfail` с ссылкой на follow-up change; в tasks — явный критерий снятия xfail.

**Почему:** сейчас поведение противоречит spec — RED без xfail блокирует CI.

### 5. Curated list для paid regression (гибрид)

**Решение:** новые contract-тесты P0 + `tests/paid_regression/CURATED.md` со списком существующих путей (`modules/billing`, `balance_manager/test_handlers_comprehensive`, turn-bot-on в dedicated suite).

**Почему:** не дублировать 400+ тестов; явный минимальный набор для free PR.

### 7. RECORD-тесты без отдельного marker

**Решение:** отдельный marker `record_when_inactive` **не вводим**; RECORD gate-тесты живут в `tests/bot_active_gates/` с тем же `@pytest.mark.bot_active_gates` и `@pytest.mark.xfail(reason="loader refactor pending")`.

**Почему:** один каталог и одна команда запуска; xfail явно отделяет «целевой контракт» от «обязан быть GREEN сейчас» (ACT P0).

### 6. Четыре обязательные ACT-категории (приоритет P0 gates)

| Категория | Coroutine / entry |
|-----------|-------------------|
| Общая ставка search | `update_common_bid_in_search_adv` |
| Target place ключей | `update_individual_keyword_target_places`, `adv_settings_auto_update` (v3) |
| Whitelist | `update_top_key_in_advs`, `white_list_tail_trimmer`, v3 whitelist в `process_adv_v3` |
| Shelf bid | `auto_shelf_bid_control` → `_set_target_bid` / `_persist_state_then_set_bid` |

Расширение P0: `update_cluster_bids`, `update_minus_phrases_in_advs`, `update_cpm_bid`.

## Affected components

| Компонент | Роль в change |
|-----------|----------------|
| `pytest.ini` | маркеры `paid_regression`, `bot_active_gates` |
| `tests/paid_regression/` | новые + README |
| `tests/bot_active_gates/` | новые + README + `helpers.py` |
| `tests/conftest.py` | корневая `access_mock` — обязательна для WBApi в suite-фикстурах |
| `CoroutinesManager` | объект тестов (мок shop data manager) |
| `WBShopDataManager._get_active_advs` | документируется в матрице; код не меняется |
| `AutoShelfBidControlManager._is_eligible` | образец существующего gate-теста |
| Billing / client_bot turn-on | curated regression list |

## Coroutine matrix (ACT vs RECORD)

Базовый список из `WBShop.run()`:

**RECORD (целевое: работает при `bot_active=False` после рефакторинга):**

- `update_advs_data_from_wb_to_pg`
- `update_cards_data_from_wb_to_pg`
- `update_common_sale_stat`
- `update_full_adv_stat`
- `update_clusters_adv_stats_today` / `_history`
- `refresh_stats_freshness_cache`
- `update_keywords_stamp` (через отдельные корутины в manager)
- `update_keywords_positions_history`
- `increment_fact_data_stats`
- `update_plan_fact_stats`
- `cache_current_cluster_bids` (read WB → write Redis)
- `preload_min_bids_cache_*` (read/cache)
- snapshot updater batch (после смены filter)

**ACT (только `bot_active=True`):**

- `adv_settings_auto_update` (v2/v3 automation)
- `update_minus_phrases_in_advs`
- `update_cluster_bids`
- `update_top_key_in_advs`
- `update_common_bid_in_search_adv`
- `auto_shelf_bid_control`
- `auto_shelf_bid_increment_stats` (если пишет WB)
- `white_list_tail_trimmer`
- `update_individual_keyword_target_places`
- `update_cpm_bid`
- `auto_reset_bid_for_auto_adv`
- `handle_stats_stale_emergency` (мутирует keyword status + bids)
- `delete_keywords_from_wl_by_mean_auto_ctr`
- `auto_budget_watchdog` (start/pause campaigns)
- `change_adv_strategy` (если применяет WB)

**Mixed / review:**

- `auto_budget_watchdog` — пополнение vs start/pause: разделить в follow-up.

## Test patterns

**Gate (inactive):**

```text
GIVEN ComplexAdv with bot_active=False
AND all relevant auto flags enabled (whitelist, target_place, shelf control, common bid)
AND downstream write inputs are non-empty when the coroutine would otherwise exit early
WHEN coroutine X runs
THEN WB write dependency mock was NOT called
```

**Paid regression (active):**

```text
GIVEN ComplexAdv with bot_active=True and flags enabled
WHEN coroutine X runs (with mocked WB success)
THEN WB write dependency mock WAS called (or manager reached apply path)
```

**Recording (inactive, xfail until loader refactor):**

```text
GIVEN adv bot_active=False, cabinet has valid token
WHEN update_keywords_stamp runs
THEN stamp manager update WAS invoked
```

**Client_bot turn on/off (paid regression):**

Handlers вызывают `async with sm(read_only=False) as session:` — `sm` в patch **должен быть callable**, возвращающий async context manager, а не сам context manager:

```python
patch("...adv_setting.sm", MagicMock(side_effect=lambda **_: _session_cm(session)))
```

`AdvSettingMenu` / `ShopMenu`: `return_value=AsyncMock()` — handler делает `await Menu(...)(...)`.

**Pricer (paid regression):**

Тест tariff count: patch `Pricer.fetch_bot_active_advs` → `[]`, assert `get_tariff_details(...).count == 0` (не legacy `get_tariff_context_for_shop`).

## Validation plan

1. `poetry run pytest tests/bot_active_gates -m bot_active_gates -v` — ACT gates GREEN (2 xfail на RECORD допустимы).
2. `poetry run pytest tests/paid_regression -m paid_regression -v` — all GREEN.
3. `poetry run pytest tests/modules/billing tests/modules/balance_manager/test_handlers_comprehensive.py -m unit -q` — curated adjunct.
4. Документировать в README: какие тесты `xfail` и когда снимать.

## Migration Plan

1. Merge только тесты + docs (zero production diff).
2. Команда free-разработки: обязательный `paid_regression` перед merge.
3. Follow-up change: refactor `_get_active_advs`, снять `xfail` на RECORD gates.
4. Follow-up: free UI bot + access guards в handlers.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Gate-тесты не ловят leak через новую корутину | Матрица в spec + checklist в PR template |
| Дублирование `bot_active` filter в coroutine и loader | Helper `is_paid_actions_enabled` в follow-up |
| `xfail` маскирует регресс RECORD | `strict=False` + отдельный marker; задача на снятие xfail с датой |
| Paid suite слишком маленький | CURATED.md + постепенное расширение |
| Shelf coroutine не фильтрует на входе | Явный gate-тест на `auto_shelf_bid_control` tick |

## Open Questions

1. Включать ли `auto_shelf_bid_increment_stats` в P0 gates (пишет ли WB напрямую)?
2. `cache_current_cluster_bids` — RECORD или ACT? (read-only с WB, write Redis — считаем RECORD.)
3. ~~Нужен ли отдельный marker `record_when_inactive`?~~ **Решено:** нет, xfail на `bot_active_gates` (см. Decision 7).
4. Follow-up: новое поле `tier` vs переиспользование `bot_active` для free/paid — решить до production free.
