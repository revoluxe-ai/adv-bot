from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.client_bot.user_interface.handlers.shop_choice_message import MainMenu
from app.client_bot.user_interface.views.gate import get_gate_keyboard, get_gate_message_text
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

        if settings.invite_gate and not user.passed_gate:
            _= await bot.send_message(
                chat_id,
                get_gate_message_text(),
                reply_markup=get_gate_keyboard(),
            )
            return
        await MainMenu(bot, chat_id)()
    return
