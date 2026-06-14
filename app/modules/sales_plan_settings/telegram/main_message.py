"""Telegram-экран настройки плана продаж без лишних UI-параметров.

Этот экран показывает и редактирует только sales-plan значения рекламной
кампании. Он работает как тонкая обвязка над ``AdvSetting`` и специально не
подключает automatic version normalization: этот workflow относится к другому
Telegram-экрану и не должен вмешиваться в логику плановых полей.
"""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import select

from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from .keyboards import KeyboardsGetter


class SalesPlanSettingsMenuMessage(TextWithKeyboard):
    """Собирает текст и клавиатуру для редактирования плана продаж.

    Экран намеренно минимален: он загружает ``AdvSetting``, показывает
    статический текст и собирает клавиатуру из текущих sales-plan значений.
    Никаких automatic-version преобразований здесь нет, чтобы не смешивать
    управление планом продаж с другими UI-контрактами.
    """

    def __init__(self, bot: Bot, chat_id: int, adv_id, state: FSMContext):
        self._adv_id = adv_id

        super().__init__(bot, chat_id)

    async def __call__(self):
        """Загрузить кампанию и отдать управление базовому рендеру шаблона.

        Метод поднимает ``AdvSetting`` по ``adv_id`` и сохраняет его в
        экземпляре, чтобы property ``keyboard`` могла собрать кнопки на основе
        актуальных значений. Это именно экран редактирования sales-plan, а не
        место для автоматической нормализации UI-версии.
        """
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
        """Построить клавиатуру из загруженного ``AdvSetting``.

        Клавиатура берётся напрямую из sales-plan полей кампании. Здесь нет
        вызова automatic version normalization по той же причине, по которой
        нет отдельной логики для других UI-контрактов: этот экран отвечает
        только за плановые параметры.
        """
        keyboard_getter = KeyboardsGetter()
        keyboard = keyboard_getter.get_keyboard(self._adv)
        return keyboard

    @staticmethod
    async def _get_adv(adv_id: int):
        """Загрузить ``AdvSetting`` по ``adv_id`` для рендера экрана."""
        stmt = select(AdvSetting).filter(AdvSetting.adv_id == adv_id)
        async with sm() as session:
            result = await session.execute(stmt)
            adv: AdvSetting = result.scalar_one()
        return adv
