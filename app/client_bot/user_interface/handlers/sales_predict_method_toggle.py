from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.client_bot.user_interface.views.callbacks import SalesPredictMethodToggle
from app.utils.db.session_maker import get_async_session_maker as sm


router = Router()


@router.callback_query(SalesPredictMethodToggle.filter())
async def toggle_sales_predict_method(
    callback_query: CallbackQuery,
    callback_data: SalesPredictMethodToggle,
    bot: Bot,
) -> None:
    new_method_str = callback_data.new_method
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    # Конвертируем строку в enum
    new_method = FactMethods(new_method_str)

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"sales_predict_method": new_method})
        )
        await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    if FactMethods(new_method) == FactMethods.DIRECT_SALES:
        status_str = "Включен режим прямого прогноза продаж"
    else:
        status_str = "Включен режим прогноза по корзинам"

    await bot.send_message(chat_id, status_str)
