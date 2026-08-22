# Decision: empty-keywords-pause-write-path

## Status

Accepted (promoted to `openspec/decisions/empty-keywords-pause-write-path/` on archive)

## Context

Автокампания может остаться без активных ключей после решений V3 updater
(force-off / выключение последнего ключа). Нужен reusable ownership: кто
детектит empty-set, кто выполняет WB pause/start для этого reason, где живёт
reason/latch перепроверки, и как это ортогонально budget/schedule
activity-control и A/B Hold freeze. Accepted registry не содержит такого
write-path (`Architecture Decision Missing` до этого proposed artifact).

## Decision

Lifecycle «keyword OFF (текущий шаг) → когда выключать больше нечего, pause как
**следующий** шаг → periodic recheck» принадлежит **отдельному owned write-path**
capability `pause-on-empty-keywords`, а не mode-defaults policy и не A/B Hold
freeze ownership.

1. **Detect empty keywords** — shop-runner auto-updater v3 apply/tick path
   **после** успешного применения keyword OFF (OFF завершён), когда на
   автокампании не осталось активных ключей из-за действий бота («выключать
   больше нечего»). Detect/pause — не тот же шаг, что сам OFF.
2. **Pause / start campaign** — **следующий** шаг после detect: переиспользует
   существующий campaign pause/start adapter (тот же класс, что
   activity-control), с **отдельным** activity reason code для empty-keywords
   (не маскировать под budget/schedule).
3. **Recheck scheduling** — shop-runner / activity-control gate читает durable
   empty-keywords pause intent/reason и периодически делает resume+recheck;
   решение снова поставить на паузу — если после recheck активных ключей снова
   нет.
4. **Stats window** — recheck и любые решения о повторном включении ключей
   MUST опираться только на доступное окно статистики ≤7 дней (текущий
   продуктовый лимит); MUST NOT требовать историю старше 7 дней.
5. **User notify** — paid Telegram UX сообщает о входе в empty-keywords pause и
   о том, что будет перепроверка; support при необходимости — `const.SUPPORT_LINK`.
6. **A/B Hold** — freeze ≠ stop: этот write-path ортогонален Hold freeze
   (как ordinary activity-control pause).

## Applies to

- Capability `pause-on-empty-keywords`
- Auto-updater v3 keyword OFF → empty-set detection
- Campaign pause/start adapters used by activity-control
- Redis (или эквивалент) campaign activity reason / empty-keywords intent
- Paid Telegram messages about this pause reason
- Recheck/resume scheduling in shop-runner

## Allowed

- Детект empty active-keyword set **после** завершения bot-driven OFF в V3
- Pause как **следующий** шаг через существующий pause adapter с новым reason code
- Periodic resume + recheck с повторной паузой при всё ещё пустом наборе
- UX-сообщение с причиной empty-keywords и фактом перепроверки
- Чтение intent в activity-control рядом с budget/schedule reasons

## Forbidden

- Считать pause **текущим** шагом вместе с OFF ключа / concurrent с OFF
- Маскировать empty-keywords pause под `TIME_SCHEDULE` / budget / cost reasons
- Реализовывать pause «заодно» внутри A/B Hold freeze write-path
- Класть defaults этого поведения в mode-defaults policy overlays
- Требовать статистику старше 7 дней для корректности recheck
- Менять V3 keyword selection / bid / whitelist / minus логику сверх хука
  empty-set → pause/recheck
- Смешивать с тарифом, disconnect `bot_active`, канал-анонсом

## Examples

Good:
- V3 apply завершает OFF последнего ON-ключа (текущий шаг) → затем reason
  `empty_keywords` → `pause_adv` (следующий шаг)
- Через интервал recheck: `start` → V3 tick → ключей нет → снова pause с тем же reason

Bad:
- Pause вызывается в том же шаге, что OFF ключа (не «следующий»)
- Pause записан как `time_schedule`, хотя причина — пустые ключи
- Recheck «ждёт 30 дней статы», которых в продукте нет
- Hold freeze path сам владеет empty-keywords pause

## Related specs

- `openspec/specs/pause-on-empty-keywords/spec.md`

## Related changes

- `openspec/changes/archive/2026-08-08-pause-auto-campaign-on-empty-keywords`
- Coexistence context: `openspec/changes/card-ab-hold-mode` (freeze ≠ stop)

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited (`mode-defaults-policy-ownership`; Hold orthogonality)
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
  (V3 `maybe_set_empty_keywords_pause_intent` → Redis intent;
  `AutoAdvActiveControlService._maybe_pause_for_empty_keywords_intent` →
  `pause_auto_campaign` + `AutoReasonCode.EMPTY_KEYWORDS` + notify)
