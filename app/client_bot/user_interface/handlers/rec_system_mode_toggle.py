from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.client_bot.user_interface.views.callbacks import ChangeRecSystemModeStatus
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()

@router.callback_query(ChangeRecSystemModeStatus.filter())
async def toggle_rec_system_mode(
    callback_query: CallbackQuery,
    callback_data: ChangeRecSystemModeStatus,
    bot: Bot,
) -> None:
    new_status: bool = callback_data.new_status
    adv_id: int = callback_data.adv_id

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.adv_id == adv_id)
            .values({"rec_system_mode": new_status})
        )
        await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    status_str = "Включен режим раскрутки РС (полок)" if new_status else "Выключен режим раскрутки РС (полок)"

    await bot.send_message(chat_id, status_str)

