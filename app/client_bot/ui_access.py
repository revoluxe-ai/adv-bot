"""Common UI access resolvers for shop and campaign levels."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.admin_access import is_bot_admin
from app.client_bot.ui_mode import UiModeService
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet


class UiAccessMode(str, Enum):
    """Effective UI access mode for rendering paid/free controls."""

    FREE = "free"
    PAID = "paid"


@dataclass(slots=True)
class UiAccessResolver:
    """Resolve effective UI access using admin override and DB state."""

    ui_mode_service: UiModeService

    async def resolve_shop_ui_access(
        self,
        user_telegram_id: int,
        session: AsyncSession,
        shop_id: str,
    ) -> UiAccessMode:
        """Resolve shop-level access for menu rendering."""
        if is_bot_admin(user_telegram_id):
            ui_mode = await self.ui_mode_service.get_user_ui_mode(user_telegram_id)
            return UiAccessMode(ui_mode)

        stmt = select(AdvSetting.id).join(AdvSetting.wb_cabinet).where(
            WBCabinet.shop_id == shop_id,
            AdvSetting.bot_active.is_(True),
        )
        result = await session.execute(stmt)
        has_paid_adv = result.first() is not None
        return UiAccessMode.PAID if has_paid_adv else UiAccessMode.FREE

    async def resolve_adv_ui_access(
        self,
        user_telegram_id: int,
        adv_setting: AdvSetting,
    ) -> UiAccessMode:
        """Resolve adv-level access for future campaign/keyword screens."""
        if is_bot_admin(user_telegram_id):
            ui_mode = await self.ui_mode_service.get_user_ui_mode(user_telegram_id)
            return UiAccessMode(ui_mode)
        return UiAccessMode.PAID if adv_setting.bot_active else UiAccessMode.FREE
