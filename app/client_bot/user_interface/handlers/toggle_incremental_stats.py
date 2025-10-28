"""
Handler для переключения режима учета продаж.

Позволяет переключаться между:
- Классическим режимом (дневные агрегаты с экстраполяцией)
- Инкрементальным режимом (почасовой учет без экстраполяции)
"""

import logging

from aiogram import Bot, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(callbacks.ToggleIncrementalStats.filter())
async def toggle_incremental_stats(
    callback_query: CallbackQuery,
    callback_data: callbacks.ToggleIncrementalStats,
    bot: Bot,
) -> None:
    """
    Переключает режим учета продаж для рекламной кампании.
    
    При включении инкрементального режима:
    - Система использует данные за точные периоды (6-24 часа)
    - Нет экстраполяции на сутки
    - Стабильные показатели в течение дня
    - Быстрее реагирует на изменения
    """
    adv_setting_original_id = callback_data.adv_setting_original_id
    assert callback_query.message is not None
    chat_id = callback_query.message.chat.id
     
    new_increment_status: bool = callback_data.new_increment_status 

    try:
        async with sm(read_only=False) as session:
            # Получаем настройки РК с загрузкой связей
            stmt = update(AdvSetting)\
                .where(AdvSetting.id == adv_setting_original_id)\
             .values({"use_incremental_stats": new_increment_status})

            await session.execute(stmt)
            await session.commit()
             
            # Формируем сообщение
            if new_increment_status:
                details = (
                    "✅ Включен инкрементальный учет:\n"
                    "• Точный учет за период без экстраполяции\n"
                    "• Стабильные показатели в течение дня\n"
                    "• Быстрая реакция на изменения"
                )
            else:
                details = "Включен классический учет (дневные агрегаты)"

            await bot.send_message(chat_id, details)

            # Обновляем меню настроек РК
            wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
            stmt_select_wb_user_cabinet = select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
            wb_user_cabinet = await session.execute(stmt_select_wb_user_cabinet)
            wb_user_cabinet = wb_user_cabinet.scalar()

            stmt_select_adv = select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
            adv = await session.execute(stmt_select_adv)
            adv = adv.scalar()
            await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()

    except Exception as exc:
        logger.error(
            f"Ошибка переключения режима учета для РК {adv_setting_original_id}: {exc}",
            exc_info=True,
        )
        raise exc


