## Why

Планируется freemium-режим в том же продукте: при `bot_active=False` кабинет должен продолжать **запись** данных (стата, снимки, диагностика), но **не выполнять** paid automation — мутации рекламы на Wildberries. Параллельно нельзя сломать текущих платных пользователей (`bot_active=True`). Сейчас `bot_active` — единый рубильник «всё или ничего»: при выключении кампания выпадает и из записи, и из автоматики. Нужен зафиксированный контракт поведения и regression suite **до** разработки free UI и рефакторинга shop-runner.

## What Changes

- Вводится явная модель **RECORD vs ACT**: запись данных кабинета не зависит от `bot_active`; мутации WB (ставки, whitelist, target place, shelf, cluster bids и т.д.) — только при `bot_active=True` (paid).
- Добавляются два набора тестов с отдельными pytest-маркерами и папками:
  - **paid regression** — при `bot_active=True` поведение совпадает с текущим production-контрактом;
  - **bot_active gates** — при `bot_active=False` запрещены четыре ключевые категории WB write (общая ставка search, target place ключей, whitelist, shelf bid) и остальные ACT-операции из матрицы.
- Документируется матрица корутин shop-runner: ACT vs RECORD (база для будущего рефакторинга `_get_active_advs`).
- В `pytest.ini` — маркеры `paid_regression` и `bot_active_gates`; README с командами запуска перед free/paid PR.
- Gate-тесты на **запись при `bot_active=False`** изначально могут быть RED (spec на будущий рефакторинг data loader) — это ожидаемо и задокументировано.

**Out of scope (этот change):**

- Реализация free UI, второго Telegram-бота, переключения tier в одном образе.
- Рефакторинг `_get_active_advs()` и разделение RECORD/ACT в production-коде (только подготовка контракта и тестов; follow-up change).
- Изменение billing, gate/invite, onboarding.
- Новое поле `tier` / `usage_mode` в БД (обсуждается в design как follow-up).

## Capabilities

### New Capabilities

- `paid-regression-suite`: контрактные тесты, гарантирующие неизменность paid-поведения при `bot_active=True` (включение бота, billing, shop-runner ACT, UI toggles с проверкой баланса).
- `bot-active-act-gates`: инварианты free/paid границы — при `bot_active=False` WB write из перечня ACT не вызывается; при включённых флагах автоматики утечки нет.
- `shop-runner-record-act-matrix`: спецификация разделения корутин shop-runner на запись (RECORD) и мутации (ACT) для кабинетов с валидным токеном.

### Modified Capabilities

- _(нет — в `openspec/specs/` нет существующих delta-spec; поведение paid фиксируется как regression baseline, free ACT gates — как новые capability)_

## Impact

- **Тестовая инфраструктура:** новые каталоги `tests/paid_regression/`, `tests/bot_active_gates/`, маркеры в `pytest.ini`, общие фикстуры `ComplexAdv` / `AdvSetting` с `bot_active` и включёнными auto-flags.
- **Shop-runner (контракт, не код в этом change):** `CoroutinesManager`, `WBShopDataManager._get_active_advs`, корутины `update_common_bid_in_search_adv`, `update_individual_keyword_target_places`, `update_top_key_in_advs`, `white_list_tail_trimmer`, `auto_shelf_bid_control`, `update_cluster_bids`, `adv_settings_auto_update`, snapshot updater batch filter.
- **Billing / client_bot:** косвенно — paid regression включает существующие billing и turn-bot-on тесты в curated list; прямых изменений кода нет.
- **CI / workflow:** рекомендуемая команда pre-merge для free-веток; опционально отдельный job на `paid_regression`.
- **Риск:** низкий для production (только тесты и docs); gate-тесты на RECORD при inactive могут падать до follow-up рефакторинга — явно помечены `xfail` или отдельным marker `record_when_inactive` до зелёного статуса.

## Intent

Зафиксировать текущее paid-поведение и целевые инварианты free/paid границы через автоматические тесты, чтобы эксперимент с бесплатным режимом не регрессил платных пользователей.

## Current behavior

- `AdvSetting.bot_active=False` исключает кампанию из `_get_active_advs()` и практически всего shop-runner pipeline, включая запись статистики и keyword stamps.
- ACT-операции дополнительно фильтруются `bot_active` в отдельных корутинах; shelf control проверяет `bot_active` внутри `_is_eligible`.
- Нет единого regression suite «paid must not break»; нет системных тестов «inactive → no WB write».

## Desired behavior

- **Paid (`bot_active=True`):** все существующие контракты остаются зелёными; suite `paid_regression` — blocking gate перед merge free-работы.
- **Free target (`bot_active=False`):** ACT не мутирует WB (4 категории + расширенная матрица); RECORD продолжает работать после follow-up рефакторинга; gate-тесты это документируют.
- Разработчик запускает одну-две команды и получает однозначный ответ: paid сломан или нет.

## Rollback idea

Удалить каталоги тестов и маркеры из `pytest.ini`; на production-код change не влияет. Если часть gate-тестов помечена `xfail`, rollback — снять каталоги без влияния на релиз.
