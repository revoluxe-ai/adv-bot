from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.client_bot.admin_access import is_bot_admin
from app.client_bot.presentation_booking_service import get_user_upcoming_booked_slot_human
from app.client_bot.user_interface.handlers.shop_choice_message import MainMenu
from app.client_bot.utils import create_user
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.settings import settings
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm


async def start_registration(message: Message, bot: Bot, state: FSMContext) -> None:
    await state.clear()
    async with sm(read_only=False) as session:
        user_id = message.from_user.id
        stmt = (
            select(User)
            .options(
                joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet)
            )
            .where(User.user_telegram_id == user_id)
        )
        result = await session.execute(stmt)
        user: User | None = result.unique().scalar_one_or_none()
        if not user:
            user = await create_user(
                session,
                user_id,
                username=message.from_user.username,
                adv_updater_user_chat_id=message.chat.id,
            )
        if isinstance(message, Message):
            chat_id = message.chat.id
        else:
            chat_id = message.message.chat.id

        if not user.passed_gate and not is_bot_admin(user_id):
            booked_slot = None
            if settings.presentation_only:
                booked_slot = await get_user_upcoming_booked_slot_human(user_id)
            await MainMenu(
                bot,
                chat_id,
                full_client_ui=False,
                booked_slot_human=booked_slot,
            )()
            return
        await MainMenu(bot, chat_id, full_client_ui=True)()
    return
