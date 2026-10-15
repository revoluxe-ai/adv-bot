from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import logging
from sqlalchemy import select
from sqlalchemy.orm import load_only
from app.client_bot.admin_access import is_bot_admin, use_minimal_presentation_ui
from app.client_bot.user_interface.handlers.invate_gate_message import InviteGateMessage
from app.client_bot.user_interface.handlers.shop_choice_message import MainMenu
from app.client_bot.user_interface.states import GateInvite
from app.client_bot.user_interface.views.gate import get_gate_keyboard, get_gate_message_text
from app.client_bot.utils import create_user
from app.settings import settings
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


async def start_registration(message: Message, bot: Bot, state: FSMContext) -> None:
    """Стартовая регистрация: User + gate или MainMenu после message ``/start``.

    **Channel subscription:** handler вызывается, когда ``/start`` прошёл whitelist
    в ``ChannelSubscriptionMiddleware`` — live ``get_chat_member`` здесь не
    делаем намеренно. Показываем «заманушный» стартовый экран; обязательная
    подписка включается на следующих апдейтах (любой callback/сообщение кроме
    whitelist). Это продуктовый контракт onboarding, не пропуск gate.

    Invite gate (``settings.invite_gate``) и phone gate — отдельные middleware /
    ветки ниже по цепочке.
    """
    if message.from_user is None:
        raise ValueError("start_registration requires message.from_user")
    from app.modules.wb_sky_mcp.bot_handlers import (
        mcp_txn_id_from_start,
        present_mcp_start,
    )

    mcp_txn_id = mcp_txn_id_from_start(message.text)
    if mcp_txn_id is not None:
        await state.clear()
        await present_mcp_start(message, mcp_txn_id)
        return
    from_user = message.from_user
    logger.debug(
        "start_registration: enter user=%s text=%r chat=%s",
        from_user.id,
        message.text,
        message.chat.id,
    )
    await state.clear()
    async with sm(read_only=False) as session:
        user_id = from_user.id
        stmt = (
            select(User)
            .options(load_only(User.id,
                               User.passed_gate,
                               ))
            .where(User.user_telegram_id == user_id)
        )
        result = await session.execute(stmt)
        user: User | None = result.unique().scalar_one_or_none()
        logger.debug(
            "start_registration: user loaded user=%s exists=%s passed_gate=%s",
            user_id,
            user is not None,
            user.passed_gate if user is not None else None,
        )
        if not user:
            user = await create_user(
                session,
                user_id,
                username=from_user.username,
                adv_updater_user_chat_id=message.chat.id,
            )
            logger.debug("start_registration: created user=%s chat_id=%s", user_id, message.chat.id)
        chat_id = message.chat.id

        minimal = use_minimal_presentation_ui(user_id, user.passed_gate)
        logger.debug(
            "start_registration: decision user=%s minimal=%s passed_gate=%s invite_gate=%s",
            user_id,
            minimal,
            user.passed_gate,
            settings.invite_gate,
        )
        if minimal:
            logger.debug("start_registration: sending minimal MainMenu user=%s", user_id)
            if settings.presentation_only and user.passed_gate is False:
                await state.set_state(GateInvite.waiting_code)
                await InviteGateMessage(bot, chat_id)()
                return
            await MainMenu(bot, chat_id, full_client_ui=False)()
            return

        if settings.invite_gate and not user.passed_gate and not is_bot_admin(user_id):
            logger.debug("start_registration: sending gate screen user=%s", user_id)
            _= await bot.send_message(
                chat_id,
                get_gate_message_text(),
                reply_markup=get_gate_keyboard(),
            )
            return
        logger.debug("start_registration: sending full MainMenu user=%s", user_id)
        await MainMenu(bot, chat_id, full_client_ui=True)()
    return
