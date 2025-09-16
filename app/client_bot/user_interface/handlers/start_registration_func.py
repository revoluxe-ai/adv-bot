from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.client_bot.user_interface.handlers.shop_choice_message import ShopChoice
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.models import RefLink, User
from app.utils.db.session_maker import get_async_session_maker as sm


async def start_registration(message: Message, bot: Bot, state: FSMContext) -> None:
    await state.clear()
    referral_link = None
    async with sm(read_only=False) as session:
        user_id = message.from_user.id
        if isinstance(message, Message) and message.text:
            text = message.text.split(" ")
            if len(text) > 1 and text[1].isdigit():
                referral_link_id = int(text[1])
                stmt = (
                    select(RefLink)
                    .options(selectinload(RefLink.referred_users))
                    .where(RefLink.id == referral_link_id)
                )
                referral_link = (await session.execute(stmt)).scalar()

        stmt = (
            select(User)
            .options(joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet))
            .where(User.user_telegram_id == user_id)
        )
        result = await session.execute(stmt)
        user: User = result.scalar()
        if not user:
            user = User(
                user_telegram_id=user_id,
                username=message.from_user.username,
                adv_updater_user_chat_id=message.chat.id,
                wb_tokens=[],
            )
            session.add(user)
            if referral_link:
                referral_link.referred_users.append(user)
            await session.commit()
            await session.refresh(user)
            wb_user_cabinets = []
        else:
            wb_user_cabinets = user.wb_user_cabinets
        if isinstance(message, Message):
            chat_id = message.chat.id
        else:
            chat_id = message.message.chat.id

        await ShopChoice(bot, chat_id, wb_user_cabinets)()
    return
