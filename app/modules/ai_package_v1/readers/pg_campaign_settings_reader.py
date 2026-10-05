"""Read-only PG reader для detailed campaign settings projection."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.ai_package_v1.scope.pg_adv_setting_inventory_reader import (
    PgAdvSettingInventoryReader,
)
from app.modules.common_slaves.wildberries.models.models import AdvSetting


class SessionMakerProtocol(Protocol):
    """Контракт фабрики async-сессий."""

    def __call__(
        self, read_only: bool = False, **kwargs: object
    ) -> async_sessionmaker[AsyncSession]:
        ...


class PgCampaignSettingsReader:
    """Загружает AdvSetting rows для assembler detailed settings snapshot."""

    def __init__(
        self,
        session_maker: SessionMakerProtocol | Callable[..., async_sessionmaker[AsyncSession]],
    ) -> None:
        self._scope_reader = PgAdvSettingInventoryReader(session_maker)

    async def load_adv_settings(self, shop_id: str) -> list[AdvSetting]:
        """Read-only SELECT in-scope inventory для shop_id.

        Args:
            shop_id: WBCabinet.shop_id.

        Returns:
            AdvSetting rows без bot_active filter.
        """
        return await self._scope_reader.load_inventory(shop_id)
