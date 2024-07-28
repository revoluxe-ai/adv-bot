import logging
import re

from aiogram.types import Message

from app.client_bot.user_interface.handlers import start
import aiogram
from aiogram import F, Router, types, Bot
from aiogram.filters import StateFilter, BaseFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet, WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from .. import states

from ..views import callbacks, messages


sm = get_async_session_maker

router = Router()

logger = logging.getLogger(__name__)

UUID_REGEX = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')


class AdminsGetShopFilter(BaseFilter):
    user_id: int

    async def __call__(self, message: Message) -> bool:
        text = message.text
        if not text:
            return False
        match_uuid = re.Pattern.match(UUID_REGEX, text)
        user_id = message.from_user.id
        if match_uuid and user_id in [373435337]:
            return True


class AdminsGetAdvByIdFilter(BaseFilter):
    user_id: int

    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id
        text = message.text
        if text.isdigit() and user_id in [373435337]:
            async with sm() as session:
                stmt = select(AdvSetting)\
                .where(AdvSetting.adv_id == int(message.text))
                adv = await session.execute(stmt)
                adv = adv.scalar()
                if adv:
                    return True

@router.message(AdminsGetShopFilter())
async def getting_shop_for_admin(message: types.Message, bot: Bot, state: FSMContext):
    text = message.text.strip()
    async with sm() as session:
        stmt = select(WBUserCabinet.id)\
            .join(WBUserCabinet.wb_cabinet).where(WBCabinet.shop_id == text)
        wb_user_cabinet_original_id = await session.execute(stmt)
        wb_user_cabinet_original_id = wb_user_cabinet_original_id.scalar()
    await state.update_data(last_wb_user_cabinet_original_id = wb_user_cabinet_original_id)

    await messages.ShopMenu(bot, message.chat.id, state, wb_user_cabinet_original_id)()


@router.message(AdminsGetAdvByIdFilter())
async def getting_adv_id(message: types.Message, bot: Bot, state: FSMContext):
    text = message.text.strip()
    adv_id = int(text)
    chat_id = message.chat.id
    await state.set_state(None)
    async with sm() as session:
        stmt = select(AdvSetting)\
        .where(AdvSetting.adv_id == adv_id)
        adv = await session.execute(stmt)
        adv: AdvSetting = adv.scalar()
    state_data = await state.get_data()
    wb_user_cabinet_original_id =  state_data['last_wb_user_cabinet_original_id']
    async with sm() as session:
        wb_user_cabinet = await session.execute(select(WBUserCabinet)\
                                                .where(WBUserCabinet.id == wb_user_cabinet_original_id))
        wb_user_cabinet = wb_user_cabinet.scalar()
    await messages.AdvSettingMenu(bot,
                                  chat_id,
                                  wb_user_cabinet,
                                  adv,
                                  )()
    return
