"""Хелперы для toast/alert при ответе на CallbackQuery.

При ``CallbackAnswerMiddleware(pre=True)`` в ``global_router`` повторный
``callback.answer()`` из хендлера невозможен — Telegram принимает один ответ.
Для кастомного текста после обработки используйте ``pre=False`` на роутере
(``flags={"callback_answer": {"pre": False}}``) и ``set_callback_toast``.
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
