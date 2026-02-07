import logging
import re

from aiogram import Bot, Router, types
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.future import select

from app.client_bot import const
from app.client_bot.user_interface.views import messages
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.shop_menu.message import ShopMenu
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()

logger = logging.getLogger(__name__)

UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class AdminsGetShopFilter(BaseFilter):
    user_id: int

    async def __call__(self, message: Message, state: FSMContext) -> bool:
        assert message
        text = message.text
        if not text:
            return False

        # Не перехватывать ввод, если админ в сцене бонусов или пополнения баланса пользователей
        current_state = await state.get_state()
        if current_state and (
            "bonus_scene" in current_state or "user_balance_scene" in current_state
        ):
            logger.debug(
                "Сообщение не обработано фильтром AdminsGetShopFilter, "
                "т.к. пользователь в bonus_scene или user_balance_scene"
            )
            return False

        match_uuid = re.Pattern.match(UUID_REGEX, text)
        tg_user = message.from_user
        if not tg_user:
            return False
        user_id = tg_user.id
        if match_uuid and user_id in const.ADMINS:
            logger.debug(f"Сообщение {text} соответствует AdminsGetShopFilter")
            return True

        return False


class AdminsGetAdvByIdFilter(BaseFilter):
    user_id: int

    async def __call__(self, message: Message) -> bool:
        assert message is not None
        user = message.from_user
        if not user:
            return False
        user_id = user.id
        text = message.text
        if not text:
            return False
        if text.isdigit() and user_id in const.ADMINS:
            async with sm() as session:
                stmt = select(AdvSetting.id).where(AdvSetting.adv_id == int(text))
                adv = await session.execute(stmt)
                adv = adv.scalar()
                return bool(adv)
        return False


@router.message(AdminsGetShopFilter())
async def getting_shop_for_admin(
    message: types.Message, bot: Bot, state: FSMContext
) -> None:
    text = message.text.strip()
    async with sm() as session:
        stmt = (
            select(WBUserCabinet.id)
            .join(WBUserCabinet.wb_cabinet)
            .where(WBCabinet.shop_id == text)
        )
        wb_user_cabinet_original_id = await session.execute(stmt)
        wb_user_cabinet_original_id = wb_user_cabinet_original_id.scalar()
    await state.update_data(
        last_wb_user_cabinet_original_id=wb_user_cabinet_original_id
    )
    await ShopMenu(
        bot,
        message.chat.id,
        state,
        wb_user_cabinet_original_id,
    )()


@router.message(AdminsGetAdvByIdFilter())
async def getting_adv_id(message: types.Message, bot: Bot, state: FSMContext) -> None:
    text = message.text.strip()
    adv_id = int(text)
    chat_id = message.chat.id
    await state.set_state()
    async with sm() as session:
        stmt_for_get_adv = select(AdvSetting).where(
            AdvSetting.adv_id == adv_id,
        )
        result = await session.execute(stmt_for_get_adv)
        adv: AdvSetting = result.scalar()
        wb_cabinet_id = adv.wb_cabinet_id

        stmt_for_user = select(User.id).where(User.user_telegram_id == chat_id)
        result = await session.execute(stmt_for_user)
        user_original_id: User = result.scalar()

        stmt_for_wb_user_cabinet = select(WBUserCabinet).where(
            WBUserCabinet.wb_cabinet_id == wb_cabinet_id,
            WBUserCabinet.user_id == user_original_id,
        )

        result = await session.execute(stmt_for_wb_user_cabinet)
        wb_user_cabinet = result.scalar()
    assert wb_user_cabinet
    assert adv
    await messages.AdvSettingMenu(
        bot,
        chat_id,
        wb_user_cabinet,
        adv,
    )()
    return
