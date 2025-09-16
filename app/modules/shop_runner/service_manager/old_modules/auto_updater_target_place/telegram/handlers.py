from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from .callbacks import AutoUpdateTargetPlaceSetting

router = Router()


@router.callback_query(AutoUpdateTargetPlaceSetting.filter())
async def set_new_status_for_auto_update_target_place_setting(
    callback_query: CallbackQuery,
    callback_data: AutoUpdateTargetPlaceSetting,
    bot: Bot,
) -> None:
    new_status = callback_data.new_status
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"auto_update_target_place": new_status})
        )
        await session.execute(stmt)
        await session.commit()
    assert callback_query.message
    chat_id = callback_query.message.chat.id

    new_status_str: str = "Включено" if new_status else "Выключено"
    await bot.send_message(
        chat_id, f"Автообновление целевой позиции в кампании {new_status_str}"
    )
