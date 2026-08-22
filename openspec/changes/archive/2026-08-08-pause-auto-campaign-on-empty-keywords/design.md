## Context

Paid auto-кампании управляются V3 updater (вкл/выкл ключей) и ортогональным
`AutoAdvActiveControlService.ensure_campaigns_active` (budget/schedule/cost →
pause/start). Сейчас last-key OFF не приводит к паузе РК: кампания может
оставаться активной без ключей. Activity reasons уже есть в Redis
(`AutoReasonCode`), но кода empty-keywords нет. Статистика для решений
updater/cost часто берётся окном по умолчанию 7 дней
(`full_wb_adv_stat` / related helpers).

Стек: Python 3.11, shop-runner, Redis reason manager, WB pause/start adapters,
paid Telegram notify. Linked North Star increment: `INC-PAUSE-01`.

## Goals / Non-Goals

**Goals:**

- Bot-driven keyword OFF = текущий шаг; когда выключать больше нечего —
  **следующий** шаг (не тот же): pause РК.
- Периодический resume + recheck; при снова пустом наборе — снова pause.
- Отдельный reason + UX пользователю.
- Явно закрыть риск «recheck ломается из-за 7 дней статы».
- Не менять остальную авто-логику.

**Non-Goals:**

- Тариф 1000₽, disconnect `bot_active`, канал-анонс, free onboarding.
- Emergency kill switch / Hold redesign.
- Расширение окна статистики WB/CH сверх текущего продукта.

## Architecture Decision References

- `openspec/decisions/mode-defaults-policy-ownership/decision.md` (Accepted) —
  defaults не трогаем; поведение не кладём в mode overlays.
- `openspec/changes/pause-auto-campaign-on-empty-keywords/decisions/empty-keywords-pause-write-path/decision.md`
  (Proposed) — ownership detect → pause/start → recheck → notify.
- Coexistence (не registry ADL, change context): card-ab-hold — freeze ≠ stop;
  ordinary activity-control pause допустим при Hold.

## Ownership & Placement

| Concern | Owner layer | Forbidden |
|---|---|---|
| Detect empty after bot OFF | auto-updater v3 apply/tick | Telegram handlers; billing |
| Pause/start WB | existing campaign control adapter / activity-control seam | invent parallel WB client |
| Reason / recheck intent | Redis campaign activity reason (+ thin durable intent if needed) | mode-defaults policy files |
| User message | paid Telegram notify path | channel/marketing copy |
| Recheck schedule | shop-runner tick / ensure_campaigns_active gate | client_bot cron separate from runner |

Placement MUST match proposed `empty-keywords-pause-write-path`.

## Decisions

### D1. Триггер: «выключать больше нечего» → pause как **следующий** шаг

**Выбор:** текущий шаг = bot-driven keyword OFF (пока есть что выключать).
После успешного применения OFF, когда активных ключей 0 («выключать больше
нечего»), **следующий** отдельный шаг = pause РК (post-apply / после
завершения OFF). Pause MUST NOT быть тем же шагом, что OFF ключа, и MUST NOT
вызываться «внутри» каждого промежуточного force_off, пока ещё есть активные
ключи.

**Альтернативы:** (a) только периодический сканер без хука apply — медленнее и
гонка с WB; (b) pause в том же шаге, что OFF / concurrent с OFF — отвергнуто
Owner («именно следующий шаг, а не текущий»).

### D2. Reason code отдельный от budget/schedule

**Выбор:** новый `AutoReasonCode` (рабочее имя `empty_keywords` / `all_keywords_off`)
+ display string в reason_display; pause/start через существующий adapter.

**Альтернативы:** переиспользовать `COST_RULE_FAILED` — Forbidden (маскировка).

### D3. Recheck при окне статы ≤7 дней

**Выбор / доказательство корректности:**

1. Триггер паузы и условие «набор пуст» опираются на **состояние ключей**
   (hard_status / active set), не на историю старше 7 дней → 7d limit **не
   блокирует** сам факт pause.
2. Recheck = периодический `start` (если нет более приоритетного pause reason:
   schedule/budget/balance) + обычный V3 tick.
3. V3 при решении снова включать ключи использует **только существующие**
   источники статы с окном ≤7 дней (как сейчас). Если данных недостаточно —
   действует текущая V3 семантика insufficient/no-data (ключ может не
   включиться) → набор остаётся пустым → снова pause с empty-keywords reason.
4. Recheck **не** ждёт и **не** запрашивает историю >7 дней; отсутствие
   длинной истории — ожидаемый режим, не ошибка конфигурации.
5. Тесты MUST зафиксировать: (a) pause без обращения к >7d; (b) recheck cycle
   с mock/stub статистики только на ≤7d всё ещё завершает pause→start→re-pause
   или pause→start→keys-on без требования >7d.

**Альтернативы:** отложить recheck до «появятся 30d» — отвергнуто (данных нет).

### D4. Приоритет vs другие activity reasons

**Выбор:** empty-keywords pause не отменяет schedule/budget/insufficient_balance.
Если сейчас вне расписания или budget stop — эти reasons остаются; empty-keywords
intent сохраняется и применяется, когда другие blockers сняты (или одновременно
как pause reason, если кампания ещё active на WB).

### D5. UX notify

**Выбор:** одно сообщение (с debounce) при входе в empty-keywords pause: причина +
что бот периодически перепроверит. Telegram payload limits
(`openspec/policies/telegram_bot_api_limits.md`). При необходимости помощи —
`const.SUPPORT_LINK` (не вместо reason).

### D6. A/B Hold

**Выбор:** не трогать Hold freeze writers; pause через ordinary activity path
остаётся ортогональным (как в card-ab-hold).

## Risks / Trade-offs

- [Ложная пауза при кратковременном empty] → debounce / только post-apply после
  реального OFF; characterization tests.
- [Activity-control сразу start обратно] → empty-keywords reason/intent MUST
  участвовать в ensure_campaigns_active (не silent ignore).
- [Hold + pause UX путаница] → copy явно «пауза из-за ключей», не «холд».
- [Spam notify] → debounce / once-per-enter.
- [7d thin stats → вечный pause/recheck loop] → accepted trade-off; UX честно
  говорит о перепроверке; не расширяем stats window в этом change.

## Migration Plan

1. Deploy code + reason enum; default behavior on for paid auto with bot_active.
2. Feature flag optional if rollback needed.
3. Rollback: flag off / skip detect hook; existing pauses remain manually
   recoverable via ordinary start paths / support.

## Open Questions

- Точный интервал recheck (константа vs reuse existing watchdog cadence) —
  выбрать минимальный reuse существующего tick `ensure_campaigns_active` /
  shop-runner loop без нового cron, если достаточно.
- Нужен ли отдельный durable PG latch помимо Redis reason — решить в apply по
  аналогии с другими reasons; предпочесть Redis reason, если его хватает для
  приоритета vs start.

## Explore notes (Owner 2026-08-08)

### Что доказывает `count_active_keywords`

Считает ключи с ``strategy_mode != OFF`` в post-apply ledger
(``CalculatedKeyword`` / tick ledger). Это **доказательство пустого
bot-intended active set** после решений V3 («выключать больше нечего»), не
live-снимка WB cluster API.

Согласовано с ledger: при apply ``hard_status`` денормализуется от
``strategy_mode`` (OFF→соответствующий hs), поэтому для bot-owned набора
mode и hard_status не разъезжаются в этом пути.

**Не доказывает само по себе:** ответ WB «фразы реально крутятся», полноту
загрузки keywords (пустой list из-за miss → ложный 0), search-ногу, Free
automation.

### Почему не latch «вход executors → выход executors»

Идея Owner: на входе preamble зафиксировать active==0; после всех executors
снова 0 → сигнал pause; если активные есть → снять блок.

**Можно было бы** сделать близкий latch, но **не на границе preamble
executors**:

```
load → UpdateContext → UpdatePipeline(preamble executors)
                     → ApplyManager (FORCE_OFF + flush)  ← тут пустеет набор
                     → Redis intent
… отдельный цикл auto_budget_watchdog.finally → ensure_campaigns_active → pause
```

1. **Семантика «снова 0» ломает last-key OFF:** вход=1, после OFF выход=0 —
   это не «снова», а «стало пусто». Условие entry_empty∧exit_empty пропускает
   главный сценарий Owner.
2. **Preamble ≠ apply:** FORCE_OFF применяется в ``ApplyManager.apply``, после
   ``UpdatePipelineManager.run_preamble``. Замер «после executors» до apply
   ещё видит последний активный ключ.
3. **Pause = следующий шаг / другой цикл:** activity-control живёт в
   ``auto_budget_watchdog`` finally (~60s), не в finally V3. Нужен durable
   сигнал (сейчас Redis intent), иначе pause в том же V3-шаге = concurrent с OFF
   (Forbidden Owner).
4. **Обратный сигнал «есть активные → блока нет»** — здравый latch-clear; сейчас
   эквивалент слабее: нет нового intent + start пишет ``BUDGET_OK_COST_OK``.
   Явный clear empty-keywords reason при active>0 можно добавить отдельно, не
   меняя detect seam.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
