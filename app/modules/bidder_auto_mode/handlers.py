from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker
from app.client_bot.user_interface.views.messages import CPMSetting
from app.client_bot.user_interface.views.callbacks import CPMSettingMenu

router = Router()

@router.callback_query(CPMSettingMenu.filter(F.action == "on_bidder_for_auto"))
async def on_bidder_for_auto(callback: CallbackQuery, callback_data: CPMSettingMenu):
    """Включает автоматический биддер для рекламной кампании"""
    async with get_async_session_maker() as session:
        # Получаем настройки рекламной кампании
        stmt = select(AdvSetting).where(AdvSetting.id == callback_data.adv_original_id)
        result = await session.execute(stmt)
        adv_setting = result.scalar_one_or_none()
        
        if not adv_setting:
            await callback.answer("Рекламная кампания не найдена")
            return

        # Включаем автоматический биддер
        adv_setting.bidder_for_auto = True
        await session.commit()

        # Обновляем сообщение с настройками
        message = CPMSetting(callback.bot, callback.message.chat.id)
        await message(callback_data.adv_original_id)
        await callback.answer("Автоматический биддер включен")

@router.callback_query(CPMSettingMenu.filter(F.action == "off_bidder_for_auto"))
async def off_bidder_for_auto(callback: CallbackQuery, callback_data: CPMSettingMenu):
    """Выключает автоматический биддер для рекламной кампании"""
    async with get_async_session_maker() as session:
        # Получаем настройки рекламной кампании
        stmt = select(AdvSetting).where(AdvSetting.id == callback_data.adv_original_id)
        result = await session.execute(stmt)
        adv_setting = result.scalar_one_or_none()
        
        if not adv_setting:
            await callback.answer("Рекламная кампания не найдена")
            return

        # Выключаем автоматический биддер
        adv_setting.bidder_for_auto = False
        await session.commit()

        # Обновляем сообщение с настройками
        message = CPMSetting(callback.bot, callback.message.chat.id)
        await message(callback_data.adv_original_id)
        await callback.answer("Автоматический биддер выключен") 