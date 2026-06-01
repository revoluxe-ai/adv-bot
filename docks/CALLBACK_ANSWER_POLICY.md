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

