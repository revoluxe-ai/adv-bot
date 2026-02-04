from aiogram import Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from app.client_bot.user_interface.message_templates.templates import TextWithKeyboard
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker
from .keyboards import WhiteListModeKeyboards


class WhiteListModeMenuMessage(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, adv_id: int):
        super().__init__(bot, chat_id)
        self._adv_id = adv_id
        self._adv: AdvSetting | None = None

    async def __call__(self):
        self._adv = await self._get_adv(self._adv_id)
        return await super().__call__()

    @property
    def text(self) -> str:
        return (
            "Выберите режим работы белого списка (БС):\n"
            """1. "Срезание хвоста" — Если внутрь БС попал ключ авто, то лежащие ниже ключи из БС переводятся в Авто (отключаются).\n"""
            "2. Активация только ключей из БС — Активируются только те ключи, которые добавлены в БС.\n"
            "3. Свободная активация ключей — авто-ключи с рейтингом выше, чем рейтинг ключей в БС автоматически активируются.\n"
        )

    @property
    def keyboard(self):
        assert self._adv is not None
        return WhiteListModeKeyboards(self._adv).build_keyboard()

    @staticmethod
    async def _get_adv(adv_id: int) -> AdvSetting:
        async with get_async_session_maker() as session:
            result = await session.execute(
                select(AdvSetting).where(AdvSetting.adv_id == adv_id)
            )
            return result.scalar_one()
