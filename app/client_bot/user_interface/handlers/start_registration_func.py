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
    async with sm(read_only=False) as session:
        if message.from_user is None: return
        user_id = message.from_user.id
        if isinstance(message, Message) and message.text:
            text = message.text.split(" ")
            if len(text) > 1 and text[1].isdigit():
                referral_link_id = int(text[1])
                stmt_ref_link = (
                    select(RefLink).options(selectinload(RefLink.referred_users)).where(RefLink.id == referral_link_id)
                )
                referral_link: RefLink | None = (await session.execute(stmt_ref_link)).scalar_one_or_none()

        stmt_user = (
            select(User)
            .options(joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet))
            .where(User.user_telegram_id == user_id)
        )
        result = await session.execute(stmt_user)
        user: User | None = result.scalar_one_or_none()
        if user is None:
            user = User()
            user.user_telegram_id = user_id
            if message.from_user is None: return
            user.username = message.from_user.username
            if message.chat is None: return
            user.adv_updater_user_chat_id = message.chat.id
            # user.wb_tokens = [] # Отношения Mapped не присваиваются напрямую таким образом
            session.add(user)
            if referral_link:
                referral_link.referred_users.append(user)
            await session.commit()
            await session.refresh(user)
            wb_user_cabinets = []
        else:
            if user is None: return
            wb_user_cabinets = user.wb_user_cabinets
        assert message.chat is not None
        chat_id = message.chat.id

        await ShopChoice(bot, chat_id, wb_user_cabinets)()
    return
