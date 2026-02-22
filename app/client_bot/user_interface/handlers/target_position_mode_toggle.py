from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.client_bot.user_interface.views.callbacks import TargetPositionModeToggle
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums import TargetPositionMode
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(TargetPositionModeToggle.filter())
async def toggle_target_position_mode(
    callback_query: CallbackQuery,
    callback_data: TargetPositionModeToggle,
    bot: Bot,
) -> None:
    new_mode_str = callback_data.new_mode
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    new_mode = TargetPositionMode(new_mode_str)

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"target_position_mode": new_mode})
        )
        await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    if new_mode == TargetPositionMode.MIN_CPA:
        status_str = "Включен режим целевой позиции по мин. CPA"
    else:
        status_str = "Включен режим целевой позиции по макс. конверсии корзины к просмотрам"

    await bot.send_message(chat_id, status_str)
