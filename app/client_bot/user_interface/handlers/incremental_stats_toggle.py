from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.client_bot.user_interface.views.callbacks import IncrementalStatsToggle
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(IncrementalStatsToggle.filter())
async def toggle_incremental_stats(
    callback_query: CallbackQuery,
    callback_data: IncrementalStatsToggle,
    bot: Bot,
) -> None:
    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == callback_data.adv_setting_original_id)
            .values({"use_incremental_stats": callback_data.new_status})
        )
        _ = await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id
    status_text = (
        "Инкрементальная статистика ПП включена"
        if callback_data.new_status
        else "Инкрементальная статистика ПП отключена"
    )
    _ = await bot.send_message(chat_id, status_text)

