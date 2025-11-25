from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from app.client_bot.user_interface.views.callbacks import AutoUpdaterVersionToggle

router = Router()


@router.callback_query(AutoUpdaterVersionToggle.filter())
async def toggle_auto_updater_version(
    callback_query: CallbackQuery,
    callback_data: AutoUpdaterVersionToggle,
    bot: Bot,
) -> None:
    new_version = callback_data.new_version
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"automatic_version": new_version})
        )
        await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    version_str: str = "V2" if new_version == 2 else "V1"
    await bot.send_message(chat_id, f"АвтоАпдейтер переключен на версию {version_str}")
