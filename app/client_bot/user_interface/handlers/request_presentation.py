"""Кнопка «Запросить презентацию»: мгновенная заявка без инвайта."""

from urllib.parse import quote

from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.const import SUPPORT_USER_NAME
from app.client_bot.support_notify import notify_presentation_request
from app.client_bot.user_interface.views.callbacks import RequestPresentation

router = Router()


@router.callback_query(RequestPresentation.filter(F.action == "request"))
async def request_presentation_start(
    callback: types.CallbackQuery,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Создает заявку на презентацию без инвайта."""
    if callback.message is None or not callback.from_user:
        return
    await state.clear()
    await notify_presentation_request(
        bot,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
    )
    chat_id = callback.message.chat.id
    telegram_id = callback.from_user.id
    prefill = (
        f"Хочу записаться на презентацию, мой TELEGRAM ID: {telegram_id}"
    )
    manager_url = (
        f"https://t.me/{SUPPORT_USER_NAME}?text={quote(prefill)}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Связаться с менеджером",
                    url=manager_url,
                )
            ]
        ]
    )
    _ = await bot.send_message(
        chat_id,
        "Заявка отправлена менеджеру. Нажмите кнопку ниже — откроется чат с текстом "
        "о записи на презентацию и вашим Telegram ID.",
        reply_markup=keyboard,
    )
    await callback.answer()
