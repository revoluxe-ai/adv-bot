## 1. Tests-first: characterization и gates

- [x] 1.1 Добавить characterization-тесты текущего scheduling ordinary V3 / structural ACT для campaign с `bot_active=True` до введения A/B Hold (базовая матрица «что вызывается»).
- [x] 1.2 Добавить unit-тесты decision setup ENTER (spec `card-ab-hold-mode`): PASS при `pay_for_order ≤ max CPO` и `views ≥ 100`; FAIL→OFF при PFO >, views < 100, PFO missing — без мока самой decision-функции.
- [x] 1.3 Добавить paired gate-тесты paid visibility: при `bot_active=False` UI entry скрыт / enable no-op; при `bot_active=True` экран доступен (spec paid-only).
- [x] 1.4 Добавить write-gate тесты structural freeze на ACTIVE/PENDING_SETUP: top-key whitelist, individual target-place, WL trim не доходят до WB write boundary; paired positive при mode OFF.
- [x] 1.5 Добавить write-gate: bidder / cluster bids остаются допустимы при ACTIVE (биддер MUST работать).
- [x] 1.6 Добавить тест interrupt: signal ENTER до apply → structural apply не вызывается, результат «safe / can continue».
- [x] 1.7 Добавить тест EXIT: после выключения ordinary target-place update снова eligible; snapshot restore не требуется.
- [x] 1.8 Добавить тест Excel apply: enable A/B Hold при `bot_active=False` не применяется.

## 2. Модель состояния и defaults

- [x] 2.1 Добавить PG-поле durable режима кампании OFF / PENDING_SETUP / ACTIVE с default OFF (миграция).
- [x] 2.2 Провести default «выкл» через mode policy overlays (accepted `mode-defaults-policy-ownership`); без прямого присваивания в transition-helper.
- [x] 2.3 Прокинуть режим в DTO кампании / ComplexAdv для scheduler и UI gates.

## 3. Redis coordination (project patterns)

- [x] 3.1 Реализовать `CardAbHoldSignal` cache (`AdvSettingRedisCache` + `RedisCacheBase`, TTL ~15 мин).
- [x] 3.2 Реализовать `CardAbHoldLastAbort` cache (safe/can_continue/reason/at, TTL ~1 ч).
- [x] 3.3 Setup lock через `RedisLockManager` с ключом `CardAbHoldSetupLock:{adv_id}` (TTL ~5 мин).
- [x] 3.4 Unit-тесты Redis roundtrip / lock NX без лишних MagicMock доменных моделей.

## 4. Setup / Hold pipelines и scheduling

- [x] 4.1 Реализовать decision + apply ENTER setup: классификация ключей, OFF на FAIL, ЦП := текущая фактическая на PASS, flush через существующий apply path.
- [x] 4.2 Реализовать hold-тик: только overspend/PFO-max guard; без TP update / WL / enable / calibration UP.
- [x] 4.3 Встроить scheduling exclusion: PENDING_SETUP→setup, ACTIVE→hold, OFF→ordinary V3; ordinary structural не schedule’ится на PENDING/ACTIVE.
- [x] 4.4 Встроить interrupt check-points (после load и до apply) в ordinary structural path.
- [x] 4.5 Добавить structural ACT guards на параллельные корутины (whitelist top-key, individual TP, trim, emergency structural) при PENDING/ACTIVE.

## 5. Paid UI и Excel

- [x] 5.1 Экран A/B Hold: инструкция (прогрев max CPO / план / полки recommend-off / не менять цену) + кнопки включить / выключить / назад.
- [x] 5.2 Handler enable: gate `bot_active`, PG PENDING_SETUP, Redis ENTER, poll last-abort / ACTIVE; docstring со ссылкой на spec.
- [x] 5.3 Handler disable: EXIT → PG OFF + signal cleanup; без restore.
- [x] 5.4 Скрыть entry при `bot_active=False`.
- [x] 5.5 Excel EDIT-колонка режима; apply только при `bot_active=True`.

## 6. Документация и проверка

- [x] 6.1 Русские docstrings на новых/изменённых публичных модулях, классах, методах и тестах с указанием spec `card-ab-hold-mode` и обоснованием.
- [x] 6.2 Прогнать focused unit + ab_hold gate tests.
- [x] 6.3 Запустить `poetry run pyright-strict` на затронутых путях (или project gate) и `git diff --check`.
- [x] 6.4 Сверить placement с proposed decision `card-ab-hold-write-path-ownership` (нет sole-if в ordinary preamble, биддер не останавливается).
