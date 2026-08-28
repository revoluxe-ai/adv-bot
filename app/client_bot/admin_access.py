"""Проверка прав администратора бота (const + env)."""

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.client_bot import const
from app.settings import settings


def is_bot_admin(telegram_id: int) -> bool:
    """Админы из ADMINS и из EXTRA_ADMIN_TELEGRAM_IDS (через запятую)."""
    if telegram_id in const.ADMINS:
        return True
    return telegram_id in settings.extra_admin_telegram_ids


def use_minimal_presentation_ui(telegram_id: int, passed_gate: bool) -> bool:
    """Always False: free client UI is the default after entry gates.

    Invite/presentation onboarding deferred for current rollout
    (``invite_gate`` default off). Helper kept for stable /start call sites.
    Legacy ``PRESENTATION_ONLY_MODE=true`` still forks keyboard in
    ``shop_choice_message`` only — not recommended; see invite-gate-deferred
    decision.

    Args:
        telegram_id: Caller Telegram id (unused; signature preserved).
        passed_gate: Whether the user passed invite gate (unused while deferred).

    Returns:
        False — callers show full free MainMenu; gate screen only if
        ``settings.invite_gate`` is explicitly enabled later.
    """
    _ = (telegram_id, passed_gate, settings.presentation_only)
    return False


class IsBotAdminFilter(BaseFilter):
    """CallbackQuery / Message: отправитель в ADMINS или EXTRA_ADMIN_TELEGRAM_IDS."""

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        return is_bot_admin(user.id)
