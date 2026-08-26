## Context

Ранее `PRESENTATION_ONLY_MODE` (default true) давал dual onboarding: minimal
presentation UI vs полный клиент. Продуктовое решение: free-бот всегда после
entry-gates; presentation dual-path убрать из UX; invite оставить опциональным;
channel subscription оставить обязательным и fail-closed.

## Goals / Non-Goals

**Goals**

- Единый free MainMenu после channel + phone (invite off by default;
  `INVITE_GATE=true` включает опциональный invite entry).
- Gate middleware без presentation fork; при `invite_gate` off — no-op.
- `/start` в whitelist invite-gate (когда gate включён).
- Runtime middleware onion: Gate → Channel → Phone (aiogram reversed).
- `use_minimal_presentation_ui` стабильно False на call sites.
- Specs и unit-тесты согласованы с этим контрактом.

**Non-Goals**

- Новый OpenSpec change ради landing/migration.
- Отключение channel subscription.
- Перенос paid/billing ownership.
- Удаление env-флага `PRESENTATION_ONLY_MODE` (legacy knob, no UX fork).

## Architecture Decision References

- `openspec/decisions/callback-start-entry-write-path/decision.md` —
  Callback Start PURE_READ / no User create; write на message `/start`.
- `openspec/changes/add-free-ui-bot-access-guards/decisions/invite-gate-deferred/decision.md`
  — invite gate off on rollout; dormant middleware paths not prod defects.
- Channel subscription fail-closed — runtime middleware contract; не ослаблять
  до fail-open.

## Ownership & Placement

- Invite gate middleware: `app/client_bot/middlewars/gate.py`
- Channel subscription: `app/client_bot/middlewars/channel_subscription.py`
- Start / Callback Start UI routing:
  `app/client_bot/user_interface/handlers/start/start.py`,
  `start_registration_func.py`
- Minimal UI helper (always False): `app/client_bot/admin_access.py`
- Settings defaults: `app/settings/settings_master.py` (`presentation_only`
  default False)

Checklist:

- [x] context-first decision lookup performed
- [x] relevant decisions cited
- [x] implementation layer matches decision (no new write on Callback Start)
- [x] no Architecture Decision Missing for this product alignment

## Decisions

1. **Presentation mode не форкает UX** — helper всегда False; gate один путь.
2. **`/start` whitelisted** при `invite_gate ∧ ¬passed_gate`, чтобы handler
   показал gate или full menu, а не middleware-steal с тем же payload.
3. **Channel subscription остаётся** отдельным middleware после/рядом с gate.
4. **Invite gate deferred (current rollout):** defaults off; prod entry =
   channel + phone only. `GateMiddleware` no-op; invite-only code paths and
   bugbot findings there are dormant until explicit `INVITE_GATE=true` + owner GO.
   See `decisions/invite-gate-deferred/decision.md`.

## Risks / Mitigations

- Регрессия «minimal menu при PRESENTATION_ONLY=true» → тесты ожидают gate
  или full free menu; env.sample помечает флаг как legacy/deferred.
- Static review flagging invite bypass in `GateMiddleware` → documented as
  NOT prod defect while `invite_gate=False`; fix only on re-enable checklist.
- Случайный fail-open channel cache → не трогать в этом выравнивании;
  держать fail-closed.
