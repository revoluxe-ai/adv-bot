"""Кнопка «Запросить презентацию»: FSM ввода инвайта и уведомление саппорта."""

from urllib.parse import quote

from aiogram import Bot, F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from app.client_bot.const import SUPPORT_USER_NAME
from app.client_bot.support_notify import notify_presentation_request
from app.client_bot.user_interface.handlers.presentation_invite import (
    normalize_invite_code,
    redeem_invite_for_presentation,
)
from app.client_bot.user_interface.states import PresentationRequest
from app.client_bot.user_interface.views.callbacks import RequestPresentation
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

router = Router()
_sm = get_async_session_maker


@router.callback_query(RequestPresentation.filter(F.action == "request"))
async def request_presentation_start(
    callback: types.CallbackQuery,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Запрашивает инвайт-код для заявки на презентацию."""
    if callback.message is None or not callback.from_user:
        return
    await state.set_state(PresentationRequest.waiting_invite)
    _ = await bot.send_message(
        callback.message.chat.id,
        "Для записи на презентацию отправьте инвайт-код одним сообщением.",
    )


@router.message(StateFilter(PresentationRequest.waiting_invite), F.text)
async def request_presentation_process_invite(
    message: types.Message,
    bot: Bot,
    state: FSMContext,
) -> None:
    if not message.text or not message.from_user:
        return
    code = normalize_invite_code(message.text)
    telegram_id = message.from_user.id
    chat_id = message.chat.id

    async with _sm(read_only=False) as session:
        user_stmt = select(User).where(User.user_telegram_id == telegram_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            _ = await bot.send_message(
                chat_id,
                "Ошибка: пользователь не найден. Попробуйте /start.",
            )
            await state.clear()
            return
        user_db_id = user.id

    ok, err = await redeem_invite_for_presentation(
        telegram_id=telegram_id,
        user_db_id=user_db_id,
        code=code,
    )
    if not ok:
        _ = await bot.send_message(chat_id, err)
        return

    await notify_presentation_request(
        bot,
        telegram_id=telegram_id,
        username=message.from_user.username,
        invite_code=code,
    )
    await state.clear()
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
                    text="Подтвердить запись на презентацию",
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
