"""Read-only PG scope query для AI Package export inventory.

Паттерн совместим с `WBShopDataManager.__get_advs(..., only_bot_active=False)`,
но не импортирует WBShopDataManager и не фильтрует по bot_active.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.ai_package_v1.scope.queries import select_shop_inventory_advs
from app.modules.common_slaves.wildberries.models.models import AdvSetting


class SessionMakerProtocol(Protocol):
    """Контракт фабрики async-сессий с read_only флагом."""

    def __call__(
        self, read_only: bool = False, **kwargs: object
    ) -> async_sessionmaker[AsyncSession]:
        ...


class PgAdvSettingInventoryReader:
    """Загружает in-scope AdvSetting rows для detailed settings assembler."""

    def __init__(
        self,
        session_maker: SessionMakerProtocol | Callable[..., async_sessionmaker[AsyncSession]],
    ) -> None:
        self._session_maker = session_maker

    @staticmethod
    def build_inventory_query(shop_id: str):
        """SQLAlchemy SELECT для shop-scoped inventory (без bot_active filter).

        Делегирует ``select_shop_inventory_advs`` — тот же grain, что
        ``PgExportShopScopeReader`` (export scope vs detailed settings reader).
        """
        return select_shop_inventory_advs(shop_id)

    async def load_inventory(self, shop_id: str) -> list[AdvSetting]:
        """Возвращает все non-done AdvSetting rows магазина (read-only session).

        Args:
            shop_id: Идентификатор магазина (WBCabinet.shop_id).

        Returns:
            Список ORM строк AdvSetting; пустой список если inventory отсутствует.
        """
        session_factory = self._session_maker(read_only=True)
        async with session_factory() as session:
            stmt = self.build_inventory_query(shop_id)
            result = await session.execute(stmt)
            return list(result.scalars().all())
