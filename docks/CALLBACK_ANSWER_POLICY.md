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

