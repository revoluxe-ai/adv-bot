from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update



from app.utils.db.session_maker import get_async_session_maker as sm

from .callbacks import BidderCoroutineTypeToggle

router = Router()


@router.callback_query(BidderCoroutineTypeToggle.filter())
async def toggle_bidder_coroutine_type(
    callback_query: CallbackQuery,
    callback_data: BidderCoroutineTypeToggle,
    bot: Bot,
) -> None:
    from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
    from app.modules.common_slaves.wildberries.models import AdvSetting
    new_type_str = callback_data.new_type
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    new_type = BidderCoroutineType(new_type_str)

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"bidder_coroutine_type": new_type})
        )
        await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    if new_type == BidderCoroutineType.OLD_UPDATE_CPM_BIDDER:
        status_str = "Переключено на стандартный режим биддера (CPM)"
    else:
        status_str = "Переключено на кластерный режим биддера"

    await bot.send_message(chat_id, status_str)









