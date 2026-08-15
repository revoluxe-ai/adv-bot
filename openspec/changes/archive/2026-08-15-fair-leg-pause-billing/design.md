## Context

При `bot_active=True` биллинг считает каждую авто-настройку как `count=1` в
`Pricer.fetch_tariff_auto_advs`, игнорируя `active_status` ног. `AdvPayment` —
одна строка на якорный `adv_setting_id` за UTC-день (`type` часто NULL).
Owner contract + proposed ADL требуют: два слота (Auto / Search) по **0.5**
тарифа за комплект, latch per leg за UTC-день, две AdvPayment-строки,
backward-compatible full charge при обеих ногах `started`, якорь по
`search_adv_id` (не по WB marketing type).

Стек: Python 3.11, SQLAlchemy/PG (`AdvSetting`, `AdvPayment`), billing loop
(`billing.py` + `RedisManager` dedup), `Pricer`, Redis (уже для
`billing_process_for_day`).

## Goals / Non-Goals

**Goals:**

- Metering: `effective_count = Σ billable_slot_weight` (0 / 0.5 за слот).
- Якорь: строка с `search_adv_id` (+ `bot_active`); Search-строка по
  `adv_id == anchor.search_adv_id`; без пары — только Auto-слот.
- Latch per leg / UTC-день в billing-owned Redis; anti-gaming.
- Две `AdvPayment` на якорь за UTC-день (`type` = `auto_leg` / `search_leg`).
- Full-charge baseline при обеих ногах `started` (сумма слотов = 1.0).
- Tolerant read legacy `AdvPayment` (`type IS NULL`).

**Non-Goals:**

- Pause-runtime, смена `tariffs_for_auto_setting`, UI disconnect, comms.
- Billing по WB marketing type 8/9.
- Latch writes из shop-runner / activity-control.

## Architecture Decision References

- `openspec/changes/fair-leg-pause-billing/decisions/billing-fair-leg-metering-write-path/decision.md`
  (Proposed) — ownership metering / latch / AdvPayment; anchor по `search_adv_id`.
- `openspec/decisions/empty-keywords-pause-write-path/decision.md` (Accepted) —
  orthogonal; billing only reads Search `active_status`.
- `openspec/decisions/auto-shelf-exhausted-pause-write-path/decision.md` (Accepted) —
  orthogonal; billing only reads anchor `active_status`.

## Ownership & Placement

| Concern | Owner layer | Forbidden |
|---|---|---|
| Anchor resolution (`search_adv_id`, `bot_active`) | `billing.pricer` + pure helper `leg_metering` | WB type labels; `bot_active` on Search-row |
| Instant slot weight (0 / 0.5) | `billing.pricer` / `leg_metering` (read PG) | shop-runner; client_bot write |
| UTC-day latch `max_billable_weight` | `billing` Redis (`RedisManager` mixin) | pause managers; activity-control |
| Cabinet debit (balance/bonus) | `billing.billing._process_single_cabinet` | Pricer side effects |
| `AdvPayment` insert | `billing.billing` only | scripts; UI |
| Tariff preview (read-only) | `Pricer.get_tariff_details` via shared `leg_metering` | duplicate formulas in client_bot |

### Semantic Write Target (durable)

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED

BUSINESS_TERM: fair leg-pause daily billing metering + AdvPayment split
TARGET_ENTITY_OR_LEG: auto-setting anchor AdvSetting; Auto/Search slots as roles; AdvPayment.type auto_leg|search_leg
ALLOWED_ADAPTERS: billing.leg_metering; billing.leg_latch; billing.pricer; billing.billing.__process_single_cabinet
FORBIDDEN_ADAPTERS: shop-runner/activity-control/pause managers (latch|AdvPayment write); client_bot charge persist; WB type-as-anchor; Search-row bot_active gate; instant-only charge without latch
TARGET_EVIDENCE: owner-contract + decisions/billing-fair-leg-metering-write-path + this design
OWNER_DECISION_SOURCE: owner-contract.md
REQUIRED_PAIRED_TESTS: see decision Semantic Write Target; tasks 2.x / 3.x / 7.x already cover paired positive/negative
```

**Design checklist**

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed (`billing-fair-leg-metering-write-path`)
- [x] implementation layer matches decision (verify at apply)

## Якорь auto-setting (алгоритм)

**Не использовать WB marketing type** для определения якоря.

1. Кандидаты: все `AdvSetting` кабинета с `bot_active=True`.
2. **Комплект с парой:** якорь = строка, у которой `search_adv_id` задан (NOT NULL
   после резолва) **и** существует связанная строка
   `AdvSetting.adv_id == anchor.search_adv_id` в том же кабинете.
3. **Комплект без пары:** якорь = `bot_active=True` строка без резолвящегося
   `search_adv_id` → только Auto-слот (Search-слот отсутствует).
4. Строка с `adv_id`, на которую ссылается чужой `search_adv_id`, **никогда**
   не якорь (даже если `bot_active` случайно True — gate только на якоре).

Слоты (роли, не WB types):

- **Auto-слот** → `active_status` якорной строки.
- **Search-слот** → `active_status` связанной строки (если пара есть).

`started` → instant weight **0.5** для слота; иначе **0.0**.

## Формула metering

```text
instant_auto  = 0.5 if anchor.active_status == "started" else 0
instant_search = 0.5 if search_row exists and search.active_status == "started" else 0
                 (no search row → slot absent, not 0 billable row)

На каждом sample в UTC-день D:
  latch_auto[D]  = max(latch_auto[D],  instant_auto)
  latch_search[D] = max(latch_search[D], instant_search)

На charge за UTC-день D:
  billable_auto   = latch_auto[D]   # уже max за день
  billable_search = latch_search[D] if search row exists else 0

per_anchor_units = billable_auto + billable_search   # 0 .. 1.0
effective_count(cabinet) = Σ per_anchor_units по всем якорям

price_per_adv = bracket(effective_count, tariffs_for_AUTO_or_OLD)
total_day = price_per_adv * effective_count / 30
```

**Backward compat:** обе ноги `started` весь день → `billable_auto=billable_search=0.5`
→ `per_anchor_units=1.0` → совпадает с legacy `count=1` для этой настройки.

## Latch SoT (Redis)

**Выбор:** Redis в `app.modules.billing.redis_manager` (новый
`BillingLegLatchMixin`), не PG — ephemeral UTC-day state, тот же контур что
`billing_process_for_day`; не дублирует pause Redis lanes.

**Ключ:** `billing:leg_latch:{anchor_adv_setting_id}:{leg_slot}:{utc_date}`

- `leg_slot` ∈ `{auto_leg, search_leg}` (стабильные строки, совпадают с
  `AdvPayment.type`).
- `utc_date` = `YYYY-MM-DD` (UTC), как `current_dt.date()` в billing loop.
- **Значение:** `"0"` или `"0.5"` (max billable weight слота).
- **TTL:** 48h (перекрывает UTC-день + повторные прогоны).
- **Write:** `SET key max(old, new)` через read-max-write в billing-owned helper
  `LegLatchManager.record_sample(...)`.
- **Read:** `get_billable_weight(anchor_id, leg_slot, utc_date)`.

**Когда sample:** в начале `_process_single_cabinet` для каждого якоря
(до расчёта цены), на **каждом** проходе billing loop за UTC-день — пока
dedup не пометил кабинет обработанным. Многократные прогоны loop (retry /
`global_ttl`) накапливают latch, закрывая gaming «pause перед единственным
charge».

**Forbidden:** обновление latch из shop-runner / pause paths.

## AdvPayment split

Использовать существующую колонку `AdvPayment.type` + unique
`(date, adv_setting_id, type)`.

| `type` | Смысл |
|---|---|
| `auto_leg` | доля дневного тарифа за Auto-слот |
| `search_leg` | доля дневного тарифа за Search-слот |
| `NULL` / legacy | исторические строки до change; **не** создавать новые |

**Запись:** только слоты с `billable_weight > 0` получают строку (0.5 → amount =
`cabinet_day_price * (billable_slot / effective_count)` при `effective_count > 0`).

`adv_setting_id` = **id якорной** строки (не Search-row id).

**Legacy read:** отчёты и dedup MUST суммировать по `(date, adv_setting_id)` с
`COALESCE(type,'legacy')`; повторный charge не вставляет дубликат благодаря
unique constraint.

**Миграция:** новый код пишет только `auto_leg` / `search_leg`; backfill старых
NULL не обязателен для go-live.

## Data flow

```text
billing loop (_process_single_cabinet)
  → load cabinet + adv_settings
  → for each anchor (bot_active, resolve search row):
       read active_status (PG)
       instant weights
       LegLatchManager.record_sample (Redis max)
  → Pricer.get_tariff_details / leg_metering.effective_count
  → if price > 0 and not already charged:
       debit cabinet (unchanged grace/block)
       insert AdvPayment auto_leg + search_leg (if billable > 0)
       set billing_process_for_day (existing Redis dedup)
```

`Pricer.get_tariff_details` MUST вызывать тот же `leg_metering` + latch read,
что billing charge (единая функция `compute_cabinet_billable_units`).

## Затронутые компоненты

| Модуль | Изменение |
|---|---|
| `app/modules/billing/leg_metering.py` (new) | anchor resolve, instant weight, effective_count |
| `app/modules/billing/leg_latch.py` (new) | Redis latch manager |
| `app/modules/billing/redis_manager.py` | mixin или делегирование latch |
| `app/modules/billing/pricer/pricer.py` | заменить count=1 на leg metering |
| `app/modules/billing/billing.py` | sample latch, split AdvPayment |
| `app/modules/billing/models.py` | константы `AdvPaymentLegType` |
| `tests/modules/billing/` | unit: weights, latch, gaming |
| `tests/integration/billing/` | PG: full/half/zero, legacy baseline |

**Не трогаем:** shop-runner pause, `redis_campaign_activity_reason_manager`,
`tariffs_for_auto_setting` цифры.

## Lifecycle

LIFECYCLE_STATUS: DERIVED

**L1. Participation gate** — якорь с `bot_active=True`; иначе не входит в Σ.
SOURCE: owner-contract.md

**L2. Instant sample** — чтение `active_status` якоря и связанной Search-строки;
instant 0 / 0.5 per slot. SOURCE: decision §2; repository `AdvSetting.active_status`

**L3. Latch accumulate (UTC-день)** — Redis `max` per leg; повторяется на каждом
проходе billing loop до dedup. SOURCE: owner-contract anti-gaming

**L4. Bracket** — `effective_count = Σ latch weights`; `price_per_adv` из таблицы.
SOURCE: owner-contract D-002

**L5. Cabinet charge** — debit balance/bonus; grace/block без изменения семантики.
SOURCE: proposal backward compat

**L6. AdvPayment artifacts** — до двух строк (`auto_leg`, `search_leg`) на якорь.
SOURCE: owner-contract D-006

## Validation plan

| Evidence role | Что доказывает |
|---|---|
| LEGACY_BASELINE | Обе ноги started → дневная сумма = legacy `count=1` |
| TARGET_REGRESSION | Одна нога paused → 0.5; обе paused → 0 |
| TARGET_REGRESSION | Нет Search, anchor started → 0.5 |
| TARGET_REGRESSION | Gaming: started ранее в UTC-день, pause перед charge → latch 0.5 |
| TARGET_REGRESSION | Две AdvPayment строки с корректными `type` |
| FINAL_ACCEPTANCE | `tests/modules/billing` + integration pricer; paid-regression billing adjunct |

Unit tests MUST NOT mock функцию, которую тестируют (weight/latch logic — real
`leg_metering` + fake Redis/in-memory).

## Performance

- Batch-load Search rows для всех `search_adv_id` кабинета одним запросом
  (избежать N+1).
- Redis latch: 2 ключа на якорь с парой × якоря кабинета — укладывается в
  существующий billing scale.
- Billing loop уже итерирует кабинеты; дополнительная работа O(anchors per cabinet).

## Rollback

1. Feature flag или revert: Pricer снова `count=len(bot_active with search_adv_id)`.
2. Отключить latch writes; single AdvPayment path.
3. Redis latch keys expire по TTL.
4. Исторические split-`AdvPayment` остаются в PG (read tolerant).

## Open Questions

- Harmless naming only: enum module name `AdvPaymentLegType` vs string constants
  в `models.py` — на усмотрение implementer.

## DESIGN_READINESS

```text
DESIGN_READINESS
PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes
DURABLE_SOT_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: yes
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
DESIGN_STATUS: READY
```
