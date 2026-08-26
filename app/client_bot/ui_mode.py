"""UI mode helpers for admin-controlled free/paid interface switching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from app.client_bot.admin_access import is_bot_admin
from app.core.redis_manager_v2.redis_client import RedisClient

UiMode = Literal["free", "paid"]

UI_MODE_REDIS_KEY_PREFIX = "ui_mode:user:"


def get_ui_mode_redis_key(user_telegram_id: int) -> str:
    """Build Redis key for a user's selected UI mode."""
    return f"{UI_MODE_REDIS_KEY_PREFIX}{user_telegram_id}"


@dataclass(slots=True)
class UiModeService:
    """Persist and resolve the interface mode for a Telegram user."""

    redis_client: RedisClient

    async def get_user_ui_mode(self, user_telegram_id: int) -> UiMode:
        """Return stored UI mode with admin-aware defaults."""
        stored_mode = await self.redis_client.get(get_ui_mode_redis_key(user_telegram_id))
        if stored_mode in {"free", "paid"}:
            return cast(UiMode, stored_mode)
        return "paid" if is_bot_admin(user_telegram_id) else "free"

    async def set_user_ui_mode(self, user_telegram_id: int, mode: UiMode) -> None:
        """Persist selected UI mode in Redis."""
        if mode not in {"free", "paid"}:
            raise ValueError(f"Unsupported UI mode: {mode}")
        await self.redis_client.set(get_ui_mode_redis_key(user_telegram_id), mode)

    async def toggle_user_ui_mode(self, user_telegram_id: int) -> UiMode:
        """Flip the stored mode between free and paid."""
        current_mode = await self.get_user_ui_mode(user_telegram_id)
        next_mode: UiMode = "free" if current_mode == "paid" else "paid"
        await self.set_user_ui_mode(user_telegram_id, next_mode)
        return next_mode

    async def should_show_paid_controls(self, user_telegram_id: int) -> bool:
        """Return True when paid controls should be visible to the user."""
        if not is_bot_admin(user_telegram_id):
            return False
        return await self.get_user_ui_mode(user_telegram_id) == "paid"
