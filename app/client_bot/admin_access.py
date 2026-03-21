"""Проверка прав администратора бота (const + env)."""

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.client_bot.const import ADMINS
from app.settings import settings


def is_bot_admin(telegram_id: int) -> bool:
    """Админы из ADMINS и из EXTRA_ADMIN_TELEGRAM_IDS (через запятую)."""
    if telegram_id in ADMINS:
        return True
    return telegram_id in settings.extra_admin_telegram_ids


def use_minimal_presentation_ui(telegram_id: int, passed_gate: bool) -> bool:
    """Минимальный экран «только презентация» — только для новых без passed_gate.

    Админы и пользователи с открытым гейтом видят полный клиентский UI на /start.
    """
    if not settings.presentation_only:
        return False
    if is_bot_admin(telegram_id):
        return False
    return not passed_gate


class IsBotAdminFilter(BaseFilter):
    """CallbackQuery / Message: отправитель в ADMINS или EXTRA_ADMIN_TELEGRAM_IDS."""

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        return is_bot_admin(user.id)
