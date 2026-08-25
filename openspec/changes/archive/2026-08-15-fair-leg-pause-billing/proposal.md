## Why

При подключённом боте ежедневное списание идёт за всю авто-настройку целиком, даже
если нога Авто или Поиск на паузе на Wildberries. Пользователь платит за
неработающую часть рекламы. Нужна честная тарификация по активным ногам, согласованная
с уже внедрёнными паузами (пустые ключи → Search, полки → Auto), без смены базовой
цены и без поломки текущего биллинга для «полностью активных» кампаний.

## What Changes

- Вводится **двухслотовая** модель metering на авто-настройку: отдельно слот **Авто**
  и слот **Поиск**; каждый слот в статусе `started` даёт **0.5** месячного тарифа
  за комплект; сумма слотов по кабинету определяет ступень тарифа.
- Ежедневное списание и **AdvPayment** разделяются на **две записи в день** (Авто /
  Поиск), а не одну агрегированную сумму «за РК».
- **Anti-gaming latch per leg:** если нога хоть раз была `started` в UTC-день,
  слот не обнуляется паузой непосредственно перед charge.
- `bot_active=False` по-прежнему исключает РК из биллинга; грация и блокировка
  кабинета без изменений семантики.
- **Совместимость со старой моделью:** при **обеих ногах в работе** итог за день
  MUST совпадать с текущим production-контрактом (полный тариф за авто-настройку);
  OLD/AUTO режимы Pricer, дедуп «один charge за UTC-день», grace/block и сценарии
  без leg-pause MUST NOT регрессировать.
- Опционально (в том же change, если узко): краткое пояснение в UI магазина, что
  списание зависит от активных ног.

## Capabilities

### New Capabilities

- `billing-fair-leg-pause`: observable контракт честного списания по ногам Авто/Поиск
  (веса 0 / 0.5 / 1.0 за комплект, latch per leg, раздельные AdvPayment, anti-gaming,
  backward-compatible full charge при обеих ногах started, bot_active gate).

### Modified Capabilities

- _(нет — в `openspec/specs/` нет существующего main spec биллинга; поведение
  фиксируется новым capability и characterization/regression против текущего
  baseline)_

## Impact

- **Billing / Pricer:** расчёт effective_count, дневной charge, разбиение AdvPayment
  по слотам; latch SoT за UTC-день.
- **Совместимость:** characterization tests «обе ноги started → как сейчас»;
  существующие billing и paid-regression сценарии MUST оставаться валидными для
  кабинетов без пауз ног; чтение исторических AdvPayment и повторный billing loop
  MUST NOT конфликтовать со старой однострочной моделью (migration/read path в design).
- **Высокий риск:** ошибки списания платы за бот (доменная зона из config).
- **Вне scope:** pause runtime, смена таблицы цен, коммуникации, retire bot_active UI,
  updater v2.

## Intent

Честно списывать только за реально работающие ноги Auto/Search, сохранив корректную
работу всего остального биллинга для уже платящих пользователей с полностью активными
настройками.

## Current behavior

- `bot_active=True` и наличие `search_adv_id` → РК считается как **1** в tariff count,
  независимо от `active_status` ног Auto/Search.
- Daily charge: одна сумма на кабинет; AdvPayment — одна запись на `adv_setting_id`
  за день, поровну между bot_active кампаниями.
- Пауза ног на WB не уменьшает списание.

## Desired behavior

- Два слота (Авто, Поиск) по 0.5 тарифа за комплект за каждый `started`-слот;
  без Search при started Auto — только слот Авто 0.5.
- Обе ноги started → **тот же** дневной итог, что сейчас (1.0 за комплект).
- Одна нога started → 0.5; обе paused → 0 за комплект в день.
- Latch per leg блокирует gaming «pause перед charge».
- Две AdvPayment-записи в день на авто-настройку (по слотам).
- Старая модель и новая **не конфликтуют**: baseline full-charge сохранён; edge
  cases только при leg-pause.

## Rollback idea

Откатить изменения Pricer/billing/AdvPayment schema и вернуть count=1 per bot_active
pair; latch storage удалить. Исторические split-записи AdvPayment останутся в БД —
rollback plan в design (read path tolerant или one-time migration revert).
