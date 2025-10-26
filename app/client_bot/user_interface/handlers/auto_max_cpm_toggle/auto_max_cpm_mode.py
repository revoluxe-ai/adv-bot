from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(
    callbacks.CPMSettingMenu.filter(F.action == "turn_on_auto_max_cpm_mode")  #ignore
)
async def turn_on_auto_max_cpm_mode(
        callback_query: CallbackQuery,
        callback_data: callbacks.CPMSettingMenu,
        bot: Bot,
) -> None:
    adv_original_id: int = callback_data.adv_original_id

    async with sm(read_only=False) as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_original_id)
            .values({"auto_max_cpm_mode": True})
        )
        await session.execute(stmt)
        await session.commit()

    chat_id = callback_query.message.chat.id
    await bot.send_message(chat_id, "АвтоМаксимальная ставка включена")
    await messages.CPMSetting(bot, chat_id)(adv_original_id)


@router.callback_query(
    callbacks.CPMSettingMenu.filter(F.action == "turn_off_auto_max_cpm_mode")
)
async def turn_off_auto_max_cpm_mode(
        callback_query: CallbackQuery,
        callback_data: callbacks.CPMSettingMenu,
        bot: Bot,
) -> None:
    adv_original_id: int = callback_data.adv_original_id

    async with sm(read_only=False) as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_original_id)
            .values({"auto_max_cpm_mode": False})
        )
        await session.execute(stmt)
        await session.commit()

    chat_id = callback_query.message.chat.id  # type: ignore[assignment]
    await bot.send_message(chat_id, "АвтоМаксимальная ставка выключена")
    await messages.CPMSetting(bot, chat_id)(adv_original_id)
