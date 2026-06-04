"""Хелперы для toast/alert при ответе на CallbackQuery.

Pre-answer: ``ImmediateCallbackAnswerUpdateMiddleware`` на Dispatcher (см.
``dispatcher_factory.install_client_bot_dispatcher_middleware``). Из хендлеров
``callback.answer()`` не вызываем.

Для toast после обработки (time_settings, префикс ``ts:``): роутерный
``CallbackAnswerMiddleware(pre=False)`` и ``set_callback_toast``. Для ошибок —
``callback.message.answer`` или ``bot.send_message``.
"""

from __future__ import annotations

from aiogram.utils.callback_answer import CallbackAnswer


def set_callback_toast(
    callback_answer: CallbackAnswer,
    text: str,
    *,
    show_alert: bool = False,
) -> None:
    """Задать текст единственного ответа middleware (режим ``pre=False``).

    Args:
        callback_answer: объект из data, инжектируется aiogram в хендлер.
        text: текст toast или alert.
        show_alert: True — модальное окно вместо краткого toast.
    """
    callback_answer.text = text
    callback_answer.show_alert = show_alert
