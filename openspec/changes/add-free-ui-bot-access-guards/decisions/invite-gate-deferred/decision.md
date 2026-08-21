# Decision: Invite gate deferred (free-bot rollout)

## Status

Accepted for `land-free-bot-rebase` / `add-free-ui-bot-access-guards` rollout

## Context

Legacy `stage` включал invite/presentation onboarding по умолчанию (`INVITE_GATE` и
`PRESENTATION_ONLY_MODE` implicit true при пустом env). Free-bot landing переводит
вход на channel + phone middleware; invite-gate **отложен** и не является prod-path
на текущем rollout.

Static review (bugbot) может находить theoretical bypass в `GateMiddleware` ниже
раннего `if not settings.invite_gate: return`. Эти ветки **недостижимы**, пока
prod/stage не выставят `INVITE_GATE=true` явно.

## Decision

1. **Production contract (current rollout):** `invite_gate=False` (default),
   `presentation_only=False` (default). Не задавать `INVITE_GATE=true` /
   `PRESENTATION_ONLY_MODE=true` в Secret/ConfigMap без отдельного owner GO.
2. **`GateMiddleware`:** при `invite_gate=False` — no-op (pass-through до handler).
   Код блокировки ниже L137 — legacy / future re-enable only.
3. **Known deferred debt** (fix only with `re-enable-invite-gate`): orphan callback
   pass-through без `chat_id`/`bot` в invite-only block. **Not a prod defect**
   while invite gate stays off.
4. **UI:** кнопки partner-invite / «Показать инвайт» — только при
   `settings.invite_gate` (сейчас скрыты).
5. **`use_minimal_presentation_ui`:** always `False`; minimal presentation keyboard
   только при явном legacy `PRESENTATION_ONLY_MODE=true` (не рекомендуется).

## Applies to

- `app/client_bot/middlewars/gate.py`
- `app/settings/settings_master.py` (`invite_gate`, `presentation_only`)
- `app/client_bot/user_interface/handlers/start/start.py` (callback Start paths)
- `app/client_bot/user_interface/handlers/shop_choice_message.py`
- `env.sample` rollout notes

## Allowed (current rollout)

- Entry: channel subscription (fail-closed) → phone → full free MainMenu
- Gate middleware registered but no-op via default settings
- Unit tests с `invite_gate=True` как regression harness для future re-enable

## Forbidden (current rollout)

- Включать `INVITE_GATE=true` на stage/prod без отдельного invite rollout
- Чинить invite-only bypass как blocking defect при выключенном gate
- Удалять gate handlers/middleware «заодно» (лишний diff; код остаётся dormant)

## Re-enable checklist (future)

- [ ] Owner GO + explicit `INVITE_GATE=true` в env
- [ ] Fail-closed orphan callback в `GateMiddleware` (TODO в коде)
- [ ] Smoke: gate screen, `passed_gate`, partner invite UX
- [ ] Обновить этот decision → promoted или superseded

## Related specs

- `openspec/changes/add-free-ui-bot-access-guards/design.md`
- `openspec/changes/add-free-ui-bot-access-guards/specs/free-client-entry/spec.md`
