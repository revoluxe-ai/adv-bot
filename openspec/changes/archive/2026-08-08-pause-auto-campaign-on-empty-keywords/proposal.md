## Evolution Context

```text
EVOLUTION_LINK: LINKED
STAR_ID: affordable-auto-pause-on-empty
INCREMENT_ID: INC-PAUSE-01
KEEP: keyword OFF (current step) → when nothing left to turn off, pause is NEXT step (not same step) + periodic recheck + user message + 7d-stats proof; no tariff/disconnect/comms
HARD: EVOLUTION_SCOPE_DRIFT if artifacts/tasks include OUT_OF_SCOPE or FUTURE_INCREMENTS
```

## Why

Когда авто-бот выключает последний активный ключ, кампания часто остаётся «живой» на WB без полезного трафика. По наблюдениям Owner (~80% кейсов) такую рекламу лучше остановить; статистика это подтверждает. Нужен честный lifecycle: выключение ключей — текущий шаг; когда выключать больше нечего — **следующий** шаг (не текущий) = пауза РК; затем периодическая перепроверка с учётом окна статистики 7 дней и понятное сообщение пользователю — без переписи остальной логики автокампании.

## What Changes

### Intent

Один результат: пока есть что выключать — текущий шаг = OFF ключа(ей); когда выключать больше нечего — **следующий** шаг (не тот же шаг, что OFF) = pause РК; система периодически включает и перепроверяет кампанию; пользователь видит отдельную причину паузы (не budget/schedule); корректность recheck доказана при лимите статистики 7 дней.

### Current behavior

- V3 auto-updater может force-off ключи; отдельного «после последнего OFF → pause РК» нет.
- `ensure_campaigns_active` / activity-control уже умеет pause/start по budget, schedule, cost — но не по empty-keywords.
- Причины паузы хранятся в Redis activity-reason; отдельного кода «все ключи OFF» нет.
- A/B Hold явно допускает ортогональный activity-control pause (freeze ≠ stop).

### Desired behavior

- Пока есть активные ключи, которые бот выключает — **текущий** шаг = OFF ключа(ей), не pause.
- Когда после bot-driven OFF выключать больше нечего (0 активных ключей) — **следующий** шаг (после завершения OFF, не concurrent с ним) = pause campaign на WB.
- Периодический resume + recheck той же РК (когда снова имеет смысл крутить / появляются кандидаты ключей); окно статы ≤7 дней MUST NOT ломать этот цикл.
- Пользователь получает сообщение: почему пауза и что будет с перепроверкой.
- Reason паузы отличим от budget/schedule.
- Остальная логика авто (ставки, whitelist, minus, target place selection) не меняется.

### Scope in

- Упорядоченный хук: keyword OFF (current) → when nothing left to turn off, pause as **next** step (auto campaigns under paid bot automation).
- Periodic resume + recheck policy, валидная при 7-day stats window.
- Distinct activity reason + user-facing UX message (Telegram limits).
- Proposed write-path architecture decision для этого lifecycle.
- Tests-first: unit/integration на lifecycle, 7d proof, coexistence с activity-control / A/B Hold orthogonality.

### Out of scope

- Смена тарифа на 1000₽ / −80% (`INC-PRICE-01`).
- Снятие UI `bot_active` OFF / миграция disconnect (`INC-DISCONNECT-01`).
- Канал-анонс и маркетинговые тексты (`INC-COMMS-01`).
- Упрощение онбординга / бесплатная простая версия (`INC-ONBOARD-01`).
- Перепись auto keyword selection, bids, whitelist/minus за пределами pause-хука.
- Free-bot / RECORD-vs-ACT рефакторинг.
- Emergency kill switch / A/B Hold redesign.

## Capabilities

### New Capabilities

- `pause-on-empty-keywords`: lifecycle keyword OFF (current) → nothing left to turn off → pause as **next** step → periodic recheck → user notify; 7-day stats compatibility.

### Modified Capabilities

- (none at main `openspec/specs/` level; capability новая)

## Impact

- Shop-runner auto-updater v3 apply/tick path (детект last-key OFF) и/или activity-control pause/start.
- Redis campaign activity reason (+ display).
- Paid Telegram UX сообщение о паузе/перепроверке (`SUPPORT_LINK` при необходимости контакта — не заменяет in-bot reason).
- Risk: ложная пауза при временном empty-set; борьба с budget/schedule start; A/B Hold freeze vs pause; неверный recheck из-за 7d stats.
- Rollback idea: feature flag / disable hook; reason code unused; resume ordinary activity-control.

## Architecture decisions

- Accepted: `openspec/decisions/mode-defaults-policy-ownership/decision.md` — не нарушать (этот change не меняет mode defaults).
- Coexistence: A/B Hold freeze ≠ stop; activity-control pause ортогонален (см. card-ab-hold design/decisions).
- **Architecture Decision Missing** для reusable ownership «empty-keywords → pause / recheck write-path» → proposed decision в этом change до apply-ready.
