from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.models import PredictCTRMode
from app.client_bot.user_interface.views.callbacks import PredictCTRModeToggle
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(PredictCTRModeToggle.filter())
async def toggle_predict_ctr_mode(
    callback_query: CallbackQuery,
    callback_data: PredictCTRModeToggle,
    bot: Bot,
) -> None:
    new_mode_str = callback_data.new_mode  # String value from callback
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    # Конвертируем строку обратно в enum для типовой безопасности
    new_mode = PredictCTRMode(new_mode_str)

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"predict_ctr_mode": new_mode})
        )
        await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    if new_mode == PredictCTRMode.V1:
        status_str = "Включен режим прогноза CTR v1 (по ID кампании)"
    else:
        status_str = "Включен режим прогноза CTR v2 (по артикулам товара)"

    await bot.send_message(chat_id, status_str)
