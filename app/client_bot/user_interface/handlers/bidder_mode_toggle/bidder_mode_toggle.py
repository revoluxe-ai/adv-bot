from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.bidder_mode import BidderMode
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(
    callbacks.CPMSettingMenu.filter(F.action == "turn_on_bidder_auto_max")
)
async def turn_on_bidder_auto_max(
    callback_query: CallbackQuery,
    callback_data: callbacks.CPMSettingMenu,
    bot: Bot,
) -> None:
    adv_original_id: int = callback_data.adv_original_id

    async with sm(read_only=False) as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_original_id)
            .values({"bidder_mode": BidderMode.BY_AUTO_MAX_CPM})
        )
        _ = await session.execute(stmt)
        await session.commit()
    assert callback_query.message is not None
    chat_id = callback_query.message.chat.id
    _ = await bot.send_message(chat_id, "Режим биддера установлен: АвтоМакс. ставка")
    await messages.CPMSetting(bot, chat_id)(adv_original_id)


@router.callback_query(
    callbacks.CPMSettingMenu.filter(F.action == "turn_on_bidder_positions")
)
async def turn_on_bidder_positions(
    callback_query: CallbackQuery,
    callback_data: callbacks.CPMSettingMenu,
    bot: Bot,
) -> None:
    adv_original_id: int = callback_data.adv_original_id

    async with sm(read_only=False) as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_original_id)
            .values({"bidder_mode": BidderMode.BY_POSITIONS})
        )
        _ = await session.execute(stmt)
        await session.commit()

    chat_id = callback_query.message.chat.id  # type: ignore[assignment]
    _ = await bot.send_message(chat_id, "Режим биддера установлен: Позиции")
    _ = await messages.CPMSetting(bot, chat_id)(adv_original_id)
