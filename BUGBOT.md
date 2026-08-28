# Bugbot — client bot callbacks

Заметки для автоматического / ручного ревью diff'ов в `app/client_bot/`.
Детальная политика ACK: **`docks/CALLBACK_ANSWER_POLICY.md`**.

---
## callback answer

Коротко, если в diff трогают `@router.callback_query` или middleware:

| | |
|---|---|
| **Кто отвечает** | Только `ImmediateCallbackAnswerUpdateMiddleware` на `Dispatcher` (outer), до handler'а |
| **Где включено** | `app/client_bot/dispatcher_factory.py` → `install_client_bot_dispatcher_middleware` |
| **В handler'е** | **Нет** `callback.answer()` / `query.answer()` — уже поздно, query занят |
| **Если нужен текст** | `callback.message.answer(...)` или `bot.send_message(...)`, не второй answer |
| **Если кнопка висит** | Ищи лишний `callback.answer()` в handler'е или pre-answer middleware сняли/переставили после Gate |
| **Код-якорь** | `app/client_bot/callback_helpers.py` |

Один query = один `answerCallbackQuery`. Второй вызов → spinner / `TelegramBadRequest`.

---

## CallbackQuery: не второй `callback.answer()`

**Severity: Medium → High (UX: «залипшие» кнопки)**

### Суть

- На `Dispatcher` уже висит **`ImmediateCallbackAnswerUpdateMiddleware`**
  (`app/client_bot/dispatcher_factory.py`).
- Он вызывает `callback.answer()` **до** handler'а.
- Повторный `callback.answer()` / `query.answer()` в handler'е — **баг**.

### Симптом

- Inline-кнопка крутит spinner / «залипает».
- В логах — `TelegramBadRequest` на `answerCallbackQuery`.
- Типично: `CheckSubscribe`, gate-callback'и, любые новые `@router.callback_query`.

### Fix

1. Убрать `callback.answer()` из handler'а.
2. Логику оставить (replay, `NeedSubscribe`, меню).
3. Текст пользователю — `callback.message.answer(...)` или `bot.send_message(...)`,
   **не** второй `callback.answer()`.

### Антипаттерн

```python
# BAD
await callback.answer("Подписка подтверждена")  # middleware уже ответил
```

```python
# OK
await do_work(...)
if callback.message is not None:
    await callback.message.answer("Готово")
```

### Regression tests

- `tests/unit/client_bot/test_check_subscribe_no_callback_answer.py`
- `tests/unit/auto_updater_v3/card_ab_hold/test_handlers_no_callback_answer.py`
- `tests/client_bot/test_channel_subscription.py` — `callback.answer.assert_not_awaited()`

### Checklist

- [ ] Новый/изменённый callback handler — нет `callback.answer()`?
- [ ] Pre-answer middleware не снят / не переехал после Gate?
- [ ] Сверка с `docks/CALLBACK_ANSWER_POLICY.md`.

---

## Не баг (onboarding / cache)

- **`/start` whitelist** в `ChannelSubscriptionMiddleware` — by design: заманушный
  entry на первом `/start`; channel gate на следующих апдейтах. См. docstring
  `channel_subscription.py`.
- **Positive Redis cache 1h** — by design: только `"1"`, ≤1 `get_chat_member`/час
  на hot path; после отписки без live-check доступ может держаться до TTL;
  `CheckSubscribe` всегда `force_refresh=True`. Не stale-subscription defect.

---

## FSM / callback ID без повторного ownership — не security bug

**Severity: не баг (review noise) → Low только как hardening**

### Суть (что часто пишут в ревью)

- Handler берёт `last_wb_user_cabinet_original_id` / `wb_user_cabinet_original_id` /
  `adv_setting_original_id` из **FSM** или **CallbackData** и грузит сущность
  без явного `User.user_telegram_id == callback.from_user.id`.
- Пример: `adv_handler` — если в FSM есть `last_wb_user_cabinet_original_id`,
  ownership не перепроверяется; иначе вызывается
  `_load_wb_user_cabinet_for_adv_in_session(..., telegram_user_id, ...)`.

Формулировка в ревью: «атакующий подставит чужой id → IDOR».

### Почему это **не** считается багом (Telegram threat model)

| Утверждение ревью | Факт |
|---|---|
| «Подделать callback_data в Telegram» | **Нельзя.** При клике бот получает ровно те байты, что были зашиты в `InlineKeyboardButton` при отправке сообщения. |
| «Записать чужой id в FSM удалённо» | **Нельзя.** FSM (Redis) привязан к `user_id` + `chat_id` этого пользователя; чужой state не доступен через Bot API. |
| «Угадать id + вызвать handler» | **Нельзя** без кнопки с этим id: `CallbackQuery` приходит только от нажатия inline-кнопки, которую бот уже отправил **этому** чату. |

Итого: классический remote IDOR «подставил чужой PK в callback» **не эксплуатируется**
обычным клиентом Telegram. Это не P0/P1 security defect.

### Когда это **станет** багом (эскалация)

Поднимать severity, только если в diff есть **дополнительный** фактор:

1. **Write-path** — `UPDATE`/`commit` по id из callback/FSM без owner check
   (`toggle_*`, `turn_adv_on`, смена настроек чужой РК). Тогда impact реальный,
   даже если id попал в callback легитимно у другого пользователя из-за бага UI.
2. **Бот отдал кнопку с чужими id** этому пользователю — баг в построении клавиатуры
   / утечка id в общий чат, не «дыра в Telegram».
3. **Не callback entrypoint** — HTTP/admin/script, где id приходит из запроса без
   auth (не относится к aiogram handler'ам).
4. **Message handler** принимает сырой id из текста пользователя без проверки.

Read-only открытие меню (`AdvSettingMenu`) по связке adv + cabinet без повторного
join на `user_telegram_id` — максимум **defense in depth**, не security finding.

### Допустимый слабый сценарий (не IDOR)

- **Stale FSM** — в state остался старый `last_wb_user_cabinet_original_id`, пользователь
  открыл другую РК; возможна несогласованность UI. Это баг UX/согласованности,
  не «доступ к чужим данным», если `adv_original_id` всё равно пришёл из своей кнопки.

### Hardening (опционально, не блокер merge)

- Всегда резолвить cabinet через
  `_load_wb_user_cabinet_for_owner_in_session` / `_load_wb_user_cabinet_for_adv_in_session`
  с `callback.from_user.id`, FSM использовать только как hint после проверки.
- Не помечать как **Bug** / **P1** в Bugbot без write-path или факторов эскалации выше.

### Антипаттерн ревью

```text
# BAD (review)
«FSM last_wb_user_cabinet_original_id без check → атакующий подделает callback → IDOR»
```

```text
# OK (review)
«Read-path: повторный owner join — hardening / stale FSM. Security: N/A unless write или
бот выдал чужие id в клавиатуре.»
```

### Checklist для Bugbot

- [ ] Entrypoint — только `CallbackQuery` от inline-кнопки бота? → подделка data **не** вектор.
- [ ] Есть `commit` / WB write / смена настроек? → **да**, owner check обязателен — иначе баг.
- [ ] Только открытие меню / read PG? → не эскалировать до security без факторов выше.
- [ ] В diff клавиатура отдаёт id без фильтра по текущему user? → **да**, это баг UI/ACL.

