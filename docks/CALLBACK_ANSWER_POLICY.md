Callback answer policy (wb-sky-bot)
==================================

Коротко:
- Используем единый, централизованный pre-answer: `ImmediateCallbackAnswerUpdateMiddleware` в Dispatcher (outer middleware).
- Middleware обязано отвечать на inline callback (callback.answer) ДО запуска handler'а и ДО любых долгих операций (DB/CH/image).
- GateMiddleware и другие роутерные middleware не должны оставлять callback неотвеченным — они НЕ должны изменять порядок middleware таким образом, чтобы pre-answer оказался после блокирующих middleware.

Практика:
- Если middleware блокирует callback (например, GateMiddleware: presentation_only), глобальный pre-answer должен выполниться раньше и не допускать «залипания» кнопок.
- Локальные fallback-патчи (временные) допустимы только в emergency и должны быть удалены после восстановления глобального решения.

Решение команды:
- Выбираем чистое решение: гарантируем наличие `ImmediateCallbackAnswerUpdateMiddleware` в Dispatcher (через `create_client_bot_dispatcher`) и документируем это требование.
- Любые изменения порядка middleware требуют ревью с проверкой поведения inline callback'ов.

Что делать при деплое:
1. Проверить, что `create_client_bot_dispatcher()` вызывается и что `install_client_bot_dispatcher_middleware(dp)` выполняется до `dp.include_router(...)`.
2. В ревью PR проверять, что не меняется порядок outer middleware так, чтобы pre-answer оказался после GateMiddleware.
3. При инциденте: разрешён временный fallback в GateMiddleware, но сразу выписать таск на восстановление глобального middleware и удалить fallback.

Decision note for reviewers (deliberate choice)
------------------------------------------------
This is an explicit, team-level decision: we use a single centralized pre-answer middleware as the canonical solution for inline callback handling.

What this means for reviewers:
- Do not request permanent local fallback patches (e.g. adding callback.answer() in GateMiddleware) as the long-term fix — those are only allowed as short-term emergency hotfixes and must be accompanied by a follow-up ticket to restore the canonical middleware.
- If a PR removes or reorders the centralized pre-answer middleware, block the change and request an RFC or explicit approval from the core bot team.
- If a temporary fallback is merged for incident mitigation, require a follow-up PR that either reinstates the global middleware or documents and justifies a permanent change.

If you disagree with this policy, open an RFC issue (label: architecture) instead of requesting ad-hoc code changes in feature PRs.

На всякий случай (кратко)
-------------------------

- **Один ACK на callback** — делает ``ImmediateCallbackAnswerUpdateMiddleware`` на
  ``Dispatcher`` до handler'а; см. ``app/client_bot/dispatcher_factory.py``.
- **Handler'ы не вызывают** ``callback.answer()`` / ``query.answer()`` — иначе
  кнопки залипают; см. ``BUGBOT.md`` для чеклиста ревью.
- **Текст пользователю** — ``message.answer`` / ``bot.send_message``, не второй answer.
- **Код-якорь:** ``app/client_bot/callback_helpers.py``.

Handlers: не вызывать второй callback.answer()
---------------------------------------------

Pre-answer middleware **уже** вызвал ``callback.answer()`` на Dispatcher до handler'а
(``app/client_bot/dispatcher_factory.py`` → ``ImmediateCallbackAnswerUpdateMiddleware``).
Краткая выжимка для кода: ``app/client_bot/callback_helpers.py``.

### Почему это важно

Telegram принимает **один** ``answerCallbackQuery`` на inline query. Повторный
``callback.answer()`` / ``query.answer()`` в handler'е:

- часто падает с ``TelegramBadRequest``;
- или пользователь видит только первый toast из middleware («Запрос в обработке»);
- inline-кнопка **залипает** (spinner), пока query не протухнет.

### Запрещено в handler'ах

```python
# Плохо — middleware уже ACK'нул query
await callback.answer("Подписка подтверждена")
await query.answer("Готово", show_alert=True)
```

### Разрешено

- Логика handler'а (replay, FSM, ``NeedSubscribe``, переход в меню).
- Текст пользователю — ``callback.message.answer(...)`` или ``bot.send_message(...)``,
  **не** второй ``callback.answer()``.

```python
# Хорошо
async def handler(callback: CallbackQuery, bot: Bot) -> None:
    await do_work(...)
    if callback.message is not None:
        await callback.message.answer("Готово")
```

### Примеры в репо

| Место | Контракт |
|-------|----------|
| ``user_subscribe_on_channel.check_subscribe`` | без ``callback.answer()`` |
| ``card_ab_hold/telegram/handlers.py`` | AST: no ``query.answer`` |
| ``card_ab_hold/telegram/confirm_handlers.py`` | ``_notify_callback_user`` → message/bot |

### Тесты

- ``tests/unit/client_bot/test_check_subscribe_no_callback_answer.py``
- ``tests/unit/auto_updater_v3/card_ab_hold/test_handlers_no_callback_answer.py``
- ``tests/client_bot/test_channel_subscription.py`` — ``callback.answer.assert_not_awaited()``

### Чеклист при ревью PR

- [ ] Новый/изменённый ``@router.callback_query`` — нет ``callback.answer()``?
- [ ] Нет «fix» через второй answer; при необходимости — message/bot?
- [ ] Pre-answer middleware не снят и не переехал после Gate?

