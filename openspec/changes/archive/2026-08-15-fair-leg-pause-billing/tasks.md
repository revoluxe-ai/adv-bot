## 1. Characterization — LEGACY_BASELINE (spec: Full-active setup matches legacy daily total)

- [x] 1.1 Зафиксировать текущее поведение `Pricer.fetch_tariff_auto_advs` / `get_tariff_details` для кабинета с `bot_active` якорями и обеими ногами `started` как `count=1` на комплект (LEGACY_BASELINE; тест MUST падать после смены формулы без обновления baseline)
- [x] 1.2 Зафиксировать текущее одно `AdvPayment` на якорь за UTC-день и сумму дневного списания для full-active комплекта (LEGACY_BASELINE; spec: Legacy charge records remain readable — контраст для миграции)

## 2. Unit — leg_metering (spec: anchor, gate, per-leg weights; plan S1–S10, S17)

- [x] 2.1 Добавить `tests/modules/billing/test_leg_metering.py`: `bot_active=False` на якоре → комплект MUST NOT входить в `effective_count` (S1; paired negative к S2)
- [x] 2.2 Тест: `bot_active=True` на якоре → комплект учитывается при прочих условиях (S2; positive gate)
- [x] 2.3 Тест: якорь по `search_adv_id` + связанная строка; Search-строка с `bot_active` MUST NOT быть якорем (S3; MUST NOT WB marketing type)
- [x] 2.4 Тест: нет резолвящейся Search-ноги → только Auto-слот, Search отсутствует (S4)
- [x] 2.5 Тест: обе ноги `started` → `per_anchor_units=1.0` (S5; TARGET_REGRESSION)
- [x] 2.6 Тест: только якорная `started` → `0.5` (S6)
- [x] 2.7 Тест: только Search `started` → `0.5` (S7)
- [x] 2.8 Тест: обе не `started` → `0` (S8)
- [x] 2.9 Тест: без Search, якорь `started` → `0.5` (S9)
- [x] 2.10 Тест: два комплекта по `0.5` → `effective_count=1.0` для ступени тарифа (S10)
- [x] 2.11 Тест: Search `pause` (empty-keywords итог) при якоре `started` → `0.5` за комплект; billing MUST NOT инициировать resume (S17)

## 3. Unit — leg_latch (spec: UTC-day anti-gaming; plan S11–S12)

- [x] 3.1 Добавить `tests/modules/billing/test_leg_latch.py` с fakeredis: `record_sample` накапливает `max` вес слота за UTC-день (S11)
- [x] 3.2 Тест: нога `started` ранее в UTC-день, затем `pause` перед charge → latch MUST оставить `0.5` (S11; gaming)
- [x] 3.3 Тест: нога не была `started` весь UTC-день → latch `0` (S12; paired negative к S11)
- [x] 3.4 Тест: latch MUST NOT обновляться от одного только `bot_active` без статуса ноги (spec: latch anti-gaming)

## 4. Реализация — `leg_metering` и `leg_latch` (design: Ownership & Placement)

- [x] 4.1 Создать `app/modules/billing/leg_metering.py`: resolve anchor по `search_adv_id`, instant weights, `effective_count`; batch-load Search rows (design §Якорь)
- [x] 4.2 Создать `app/modules/billing/leg_latch.py` + mixin в `redis_manager.py`: ключ `billing:leg_latch:{anchor_id}:{leg_slot}:{utc_date}`, TTL 48h, `max(old,new)` (design §Latch SoT)
- [x] 4.3 Добавить константы `AdvPaymentLegType` (`auto_leg` / `search_leg`) в `models.py` (harmless naming из design Open Questions)

## 5. Реализация — Pricer (design: единая формула preview и charge)

- [x] 5.1 Заменить `count=1` в `fetch_tariff_auto_advs` / tariff context на `leg_metering` + latch read (`compute_cabinet_billable_units`)
- [x] 5.2 Обновить `get_tariff_details` — MUST использовать ту же функцию, что billing charge (design Data flow)
- [x] 5.3 Обновить/добавить unit-тесты `test_pricer_tariffs.py` под slot-based `effective_count` (не ломать таблицу `tariffs_for_auto_setting`)

## 6. Реализация — billing loop (design: sample → charge → split AdvPayment)

- [x] 6.1 В `_process_single_cabinet`: для каждого якоря sample instant weights → `LegLatchManager.record_sample` до расчёта цены (L3)
- [x] 6.2 При charge: debit balance/bonus без изменения grace/block семантики (L5; spec backward compat)
- [x] 6.3 Писать отдельные `AdvPayment` только для billable слотов (`auto_leg`, `search_leg`); `adv_setting_id` = якорь; MUST NOT создавать нулевые строки (S13–S14)
- [x] 6.4 Legacy tolerant read: dedup/отчёт MUST учитывать `type IS NULL` без ложного «не списано» (S16)
- [x] 6.5 MUST NOT вызывать pause/start WB из billing path (spec: Billing does not drive pause runtime)

## 7. Integration — TARGET_REGRESSION (plan S5–S18; scenario-coverage `sceplan-b5276a80b9ef69a1`)

- [x] 7.1 Integration: full-active комплект → суммарная сумма за UTC-день = LEGACY_BASELINE total (S15; FINAL_ACCEPTANCE)
- [x] 7.2 Integration: одна нога paused весь день → половина тарифа; обе paused → ноль (S6–S8)
- [x] 7.3 Integration: gaming — sample `started` утром, `pause` перед charge → Search slot `0.5` (S11)
- [x] 7.4 Integration: две строки `AdvPayment` при обоих billable слотах; одна строка при одном (S13–S14)
- [x] 7.5 Integration e2e: Search не `started` весь день, якорь `started` → debit за `0.5`, одна `auto_leg` строка (S18)

## 8. Финальные gates

- [x] 8.1 `poetry run pytest -m unit tests/modules/billing/ -v`
- [x] 8.2 `poetry run pytest -m integration tests/integration/billing/ -v` (или targeted integration billing)
- [x] 8.3 `poetry run pyright-strict` для изменённых модулей billing
- [x] 8.4 Прогнать существующие `tests/modules/billing/test_billing.py` — grace/block/dedup MUST NOT регрессировать (spec: backward-compatible full charge baseline)
