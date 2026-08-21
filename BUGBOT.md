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
