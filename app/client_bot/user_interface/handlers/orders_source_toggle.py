from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.client_bot.user_interface.views.callbacks import OrdersSourceToggle
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(OrdersSourceToggle.filter())
async def toggle_orders_source(
    callback_query: CallbackQuery,
    callback_data: OrdersSourceToggle,
    bot: Bot,
) -> None:
    new_source_str = callback_data.new_source  # String value from callback
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    # Конвертируем строку обратно в enum для типовой безопасности
    new_source = OrdersSourceForAutoMode(new_source_str)

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"orders_source_for_auto_mode": new_source})
        )
        await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    if new_source == OrdersSourceForAutoMode.ADV_SUM:
        status_str = "Включен режим анализа только рекламных заказов"
    else:
        status_str = "Включен режим анализа общей статистики заказов"

    await bot.send_message(chat_id, status_str)
