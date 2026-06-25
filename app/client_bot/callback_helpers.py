"""Политика ACK на CallbackQuery в клиентском боте.

Pre-answer: ``ImmediateCallbackAnswerUpdateMiddleware`` на Dispatcher (см.
``dispatcher_factory.install_client_bot_dispatcher_middleware``). Из хендлеров
``callback.answer()`` не вызываем.

Для пояснений после действия — ``callback.message.answer`` или
``bot.send_message``, не второй ``callback.answer``.
"""
