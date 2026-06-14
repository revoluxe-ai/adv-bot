"""Telegram-экран настройки плана продаж без лишних UI-параметров."""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import select

from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.automatic_version_ui import (
    normalize_automatic_version_ui,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from .keyboards import KeyboardsGetter


class SalesPlanSettingsMenuMessage(TextWithKeyboard):
    """Собирает текст и клавиатуру для редактирования плана продаж."""

    def __init__(self, bot: Bot, chat_id: int, adv_id, state: FSMContext):
        self._adv_id = adv_id

        super().__init__(bot, chat_id)

    async def __call__(self):
        adv: AdvSetting = await self._get_adv(self._adv_id)
        self._adv = adv
        await super().__call__()

    @property
    def text(self) -> str:
        text = """
Задать или изменить плановые показатели РК
        """
        return text

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        keyboard_getter = KeyboardsGetter()
        keyboard = keyboard_getter.get_keyboard(self._adv)
        return keyboard

    @staticmethod
    async def _get_adv(adv_id: int):
        stmt = select(AdvSetting).filter(AdvSetting.adv_id == adv_id)
        async with sm() as session:
            result = await session.execute(stmt)
            adv: AdvSetting = result.scalar_one()
        return adv
