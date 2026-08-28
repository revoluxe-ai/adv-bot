"""Telegram-сообщение выбора режима БС с передаваемой PG read-сессией."""

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.ui_access import UiAccessMode
from app.client_bot.user_interface.message_templates.templates import TextWithKeyboard
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker
from .keyboards import WhiteListModeKeyboards


class WhiteListModeMenuMessage(TextWithKeyboard):
    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        adv_id: int,
        ui_access: UiAccessMode | None = None,
    ):
        super().__init__(bot, chat_id)
        self._adv_id = adv_id
        self._adv: AdvSetting | None = None
        self._ui_access = ui_access

    async def __call__(self):
        self._adv = await self._get_adv(self._adv_id)
        if self._ui_access is None:
            self._ui_access = (
                UiAccessMode.PAID if self._adv.bot_active else UiAccessMode.FREE
            )
        return await super().__call__()

    @property
    def text(self) -> str:
        if self._ui_access == UiAccessMode.FREE:
            return (
                "Выберите режим работы белого списка (БС):\n"
                '1. "Активация только ключей из БС" — активируются только те ключи, '
                "которые добавлены в белый список.\n"
                '2. "Свободная активация ключей" — активируются авто-ключи, '
                "чей рейтинг выше минимального рейтинга ключей в БС.\n"
            )
        return (
            # TODO: "Срезание хвоста" - это доступно только для V2 - исправить
            "Выберите режим работы белого списка (БС):\n"
            """1. "Срезание хвоста" — Если внутрь БС попал ключ авто, то лежащие ниже ключи из БС переводятся в Авто (отключаются).\n"""
            """2. "Срезание хвоста с замещением" — После срезания хвоста из БС добирается такое же количество следующих авто-ключей.\n"""
            "3. Активация только ключей из БС — Активируются только те ключи, которые добавлены в БС.\n"
            "4. Свободная активация ключей — авто-ключи с рейтингом выше, чем рейтинг ключей в БС автоматически активируются.\n"
        )

    @property
    def keyboard(self):
        assert self._adv is not None
        assert self._ui_access is not None
        return WhiteListModeKeyboards(self._adv, self._ui_access).build_keyboard()

    @staticmethod
    async def _get_adv_in_session(
        session: AsyncSession,
        adv_id: int,
    ) -> AdvSetting:
        """Загрузить РК в переданной read-only PG-сессии."""
        result = await session.execute(
            select(AdvSetting).where(AdvSetting.adv_id == adv_id)
        )
        return result.scalar_one()

    @staticmethod
    async def _get_adv(adv_id: int) -> AdvSetting:
        """Загрузить РК, создав короткую read-only PG-сессию."""
        async with get_async_session_maker(read_only=True) as session:
            return await WhiteListModeMenuMessage._get_adv_in_session(
                session, adv_id
            )
