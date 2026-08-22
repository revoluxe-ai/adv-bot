# Decision: billing-fair-leg-metering-write-path

## Status

Accepted

## Context

В registry нет accepted decision для ownership fair leg-pause **metering** и
daily charge. Существующие pause write-path decisions
(`empty-keywords-pause-write-path`, `auto-shelf-exhausted-pause-write-path`)
владеют WB pause/start и activity reasons; они **не** MUST тарифицировать и
**не** MUST писать AdvPayment.

Сейчас `Pricer` / `billing` считают bot_active пару как count=1 без учёта
`active_status` ног; `AdvPayment` — одна строка на `adv_setting_id` за UTC-день.
Change `fair-leg-pause-billing` вводит два слота (Auto / Search) по 0.5 тарифа,
latch per leg за UTC-день и две AdvPayment-записи. Без reusable placement rule
metering может «утечь» в shop-runner (pause side-effects), client_bot (UI preview
как SoT) или snapshot-only WB status в секунду charge.

`AdvPayment` уже имеет колонку `type` и unique
`(date, adv_setting_id, type)` — подходит для раздельных слотов без нового
billing write-owner.

## Decision

Reusable ownership для **fair leg-pause billing metering** (read + latch + charge
artifact), ортогонально pause-runtime:

1. **AUTO-SETTING ANCHOR (какая РК «основная»).** Единицей биллинга остаётся
   **авто-настройка** — комплект, который пользователь подключает к боту.
   **Якорная** (primary) строка определяется **структурно**, не по marketing
   type WB (тип РК на WB дрифтит — **запрещено** использовать type 8/9 или
   аналоги как критерий якоря):

   - **Комплект с парой:** якорь = `AdvSetting`, у которой задан
     `search_adv_id` (ссылается на `adv_id` второй ноги комплекта). На якоре —
     `bot_active`, флаги авто-настроек (`auto_update_*`, `automatic_version`).
     **Связанная Search-нога** = отдельная `AdvSetting`, где
     `adv_id == anchor.search_adv_id`; она **не** якорь и **не** несёт
     `bot_active` gate для биллинга.
   - **Комплект без пары:** якорь = `bot_active=True` строка без резолвящегося
     `search_adv_id` (только первичный слот комплекта; Search-слот отсутствует).

   Слоты биллинга (Auto / Search) — **роли в паре**, не WB type labels:
   - **Auto-слот** = `active_status` **якорной** строки;
   - **Search-слот** = `active_status` связанной строки по `search_adv_id`,
     если пара есть.

   В runtime якорь обычно совпадает с `ComplexAdv._adv_setting`, но критерий
   SoT — **`search_adv_id` на якоре + `bot_active` gate**, не имя поля в DTO.

   `AdvPayment.adv_setting_id` MUST всегда указывать на **якорную** строку;
   слот Auto/Search различается полем `type`, а не вторым `adv_setting_id`.

2. **READ / METERING OWNER = `app.modules.billing.pricer` (+ shared pure helpers
   в billing package).** Вычисление instant leg weight (0 / 0.5 за слот) MUST
   читать только:
   - `bot_active` gate на **якорной** AdvSetting (строка с `search_adv_id` в
     паре, иначе единственная `bot_active` строка комплекта);
   - **Auto-слот:** `active_status` якорной строки;
   - **Search-слот:** `active_status` связанной строки
     (`adv_id == anchor.search_adv_id`), если `search_adv_id` задан и строка
     найдена;
   - при отсутствии связанной Search-строки (`search_adv_id` NULL / не
     резолвится) и `started` на якоре — только Auto-слот 0.5.
   `effective_count` кабинета = **сумма** billable слотов (0.5 + 0.5 = 1.0).

3. **LATCH SoT OWNER = billing module** (durable per auto-setting anchor, per leg,
   per UTC-day). Latch MUST хранить `max_billable_weight` слота (0 или 0.5) за
   UTC-день; обновление latch MUST NOT зависеть только от мгновенного
   `active_status` в секунду daily charge. Latch MUST NOT писаться из
   shop-runner pause/start, activity-control или pause reason managers.

4. **CHARGE / AdvPayment WRITE OWNER = `app.modules.billing.billing`**
   (`_process_single_cabinet` seam). Daily cabinet debit (balance/bonus) и
   `AdvPayment` MUST создаваться здесь. Две записи за UTC-день на **якорной**
   auto-setting (`adv_setting_id` = anchor id): `type` различает слот **Auto**
   и **Search** (конкретные enum/string — в design); amount = доля дневного
   тарифа за слот после latch.

5. **BACKWARD COMPAT:** при обеих ногах `started` и latch=full за UTC-день
   суммарный дневной charge за комплект MUST совпадать с legacy baseline
   (полный тариф). Чтение legacy `AdvPayment` без `type` / с legacy type MUST
   оставаться tolerant (design migration).

6. **ORTHOGONALITY:** pause-runtime (empty-keywords, shelf-exhausted, schedule,
   budget) MUST NOT вызывать charge и MUST NOT менять latch напрямую; billing
   только **читает** итоговый WB `active_status` + свой latch SoT.

## Semantic Write Target

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED

BUSINESS_TERM: fair leg-pause daily billing (Auto/Search slots 0.5 each; UTC-day latch; split AdvPayment)

TARGET_ENTITY_OR_LEG:
  - billing unit = auto-setting **anchor** AdvSetting (structural: search_adv_id on anchor OR unpaired bot_active row)
  - Auto-slot = active_status of **anchor** row
  - Search-slot = active_status of linked AdvSetting where adv_id == anchor.search_adv_id (if resolvable)
  - AdvPayment.adv_setting_id ALWAYS = anchor id; slot distinguished by AdvPayment.type = auto_leg | search_leg

ALLOWED_ADAPTERS:
  - app.modules.billing.leg_metering (anchor resolve, instant weight, effective_count)
  - app.modules.billing.leg_latch / billing Redis latch keys billing:leg_latch:*
  - app.modules.billing.pricer.Pricer (read/preview via shared metering)
  - app.modules.billing.billing.__process_single_cabinet / _process_single_cabinet (cabinet debit + AdvPayment insert)

FORBIDDEN_ADAPTERS:
  - shop-runner / activity-control / pause managers writing latch or AdvPayment
  - client_bot / export scripts persisting charge
  - WB marketing type (8/9) as anchor/slot criterion
  - bot_active on Search-linked row as participation gate
  - snapshot-only charge from instant active_status without UTC-day latch
  - pause-reason Redis lanes as billing SoT

TARGET_EVIDENCE:
  - owner-contract.md §§ «Решения Owner» (two slots 0.5; latch per leg; two AdvPayment lines)
  - this decision §§ Decision / Allowed / Forbidden
  - design.md §§ Ownership & Placement, AdvPayment split, Latch SoT
  - implemented symbols: leg_metering.py, leg_latch.py, billing.py::__process_single_cabinet, models.AdvPaymentLegType

OWNER_DECISION_SOURCE:
  openspec/changes/fair-leg-pause-billing/owner-contract.md (reviewed)

REQUIRED_PAIRED_TESTS:
  - positive: both legs started → full tariff + two AdvPayment rows (auto_leg + search_leg)
  - negative: bot_active=False on anchor → no charge / not in effective_count
  - positive: latch keeps 0.5 after same-UTC-day pause before charge
  - negative: leg never started whole UTC-day → slot stays 0
  - positive: legacy AdvPayment type NULL remains readable / dedup-safe
```

## Applies to

- `app.modules.billing.pricer` (`calculate_tariff_context`, tariff preview)
- `app.modules.billing.billing` (daily loop, cabinet debit, AdvPayment)
- Latch storage (Redis/PG — concrete choice in design, owner layer = billing)
- `AdvPayment.type` semantics for Auto / Search slots
- Characterization/regression: full-charge baseline, leg-pause half/zero, gaming

## Allowed

- Pricer: pure/read-only leg weight + effective_count aggregation
- Billing: latch update on billing tick and/or scheduled sampling before charge
  (design); apply `max(instant, latched)` per leg per UTC-day at charge time
- Billing: two `AdvPayment` rows per auto-setting per UTC-day (`type` = Auto /
  Search)
- Client_bot / scripts: **read** Pricer preview APIs; MUST NOT persist charge
- Shop-runner: continues pause/start; exposes WB `active_status` via PG only

## Forbidden

- Тарификация по `bot_active` на **связанной Search-строке** (`adv_id ==
  anchor.search_adv_id`) — gate только на **якоре** (строка с `search_adv_id`)
- Определение якоря / слота по **WB marketing type** (type 8/9 и аналоги) —
  тип РК на WB дрифтит; критерий только `search_adv_id` + `bot_active`
- Shop-runner, activity-control, pause managers writing latch or AdvPayment
- Computing final daily charge only in client_bot or export scripts
- Snapshot-only metering: charge from instant WB status without UTC-day latch
- Pause reason Redis lanes as billing SoT (read-only diagnostic at most)
- `bot_active` latch substitute for leg latch (`bot_active` = participation gate
  only)
- Breaking legacy full-charge total when both legs started entire UTC-day

## Examples

**Good**

- Empty-keywords pause sets Search `pause` via activity-control; billing reads
  Search `active_status` + latch; Auto slot still 0.5 if Auto `started`; charge
  in `billing._process_single_cabinet` writes two AdvPayment rows.

- User pauses Search 1 minute before charge but Search was `started` earlier same
  UTC-day → Search slot bills 0.5 via latch.

**Bad**

- `auto_adv_active_control_service` updates Redis latch on pause — violates
  billing ownership.

- `Pricer.get_tariff_details` at charge time reads only current `active_status`
  with no latch — gaming allowed.

- Single AdvPayment per day without `type` split after migration — violates
  Owner separate line items.

## Related specs

- Change delta: `openspec/changes/fair-leg-pause-billing/specs/billing-fair-leg-pause/spec.md`
  (when created)
- Orthogonal: `openspec/specs/pause-on-empty-keywords/spec.md`,
  `openspec/specs/auto-shelf-exhausted-pause/spec.md`

## Related changes

- `fair-leg-pause-billing` (proposes this decision)
- Evolution: `INC-BILL-LEG-PAUSE-01` in
  `openspec/evolution/affordable-auto-pause-on-empty.md`

## Review checklist

- [x] existing decisions searched (`openspec/decisions/index.md` — no billing metering ADL)
- [x] relevant decisions cited (pause write-paths orthogonal)
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision (verify at apply)
