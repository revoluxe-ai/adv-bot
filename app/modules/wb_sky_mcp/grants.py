"""Текущие магазины принципала из живой связи кабинета.

Источник прав — ``WBUserCabinet`` → ``WBCabinet.shop_id``. Токен магазины
не содержит.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.common_slaves.wildberries.models.models import WBUserCabinet
from app.modules.wb_sky_mcp.errors import McpError, McpStorageError


@dataclass(frozen=True, slots=True)
class ShopGrant:
    """Один магазин, доступный принципалу прямо сейчас."""

    shop_id: str
    name: str
    active: bool


class ShopGrantReader(Protocol):
    """Чтение кабинетов. Ошибка PostgreSQL — fail-closed."""

    async def list_shops(self, user_id: int) -> list[ShopGrant]: ...


class MemoryShopGrantReader:
    """Тестовый край БД: отдаёт заранее заданные связи пользователя."""

    def __init__(self, rows: dict[int, list[ShopGrant]] | None = None) -> None:
        self.rows = rows if rows is not None else {}
        self.fail = False

    async def list_shops(self, user_id: int) -> list[ShopGrant]:
        if self.fail:
            raise McpStorageError("postgresql unavailable")
        return list(self.rows.get(user_id, []))


class SqlShopGrantReader:
    """Живые кабинеты пользователя. Чужие ``user_id`` не читаются."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_shops(self, user_id: int) -> list[ShopGrant]:
        """Вернуть магазины только этого ``User.id``.

        Raises:
            McpStorageError: PostgreSQL недоступен.
        """
        try:
            stmt = (
                select(WBUserCabinet)
                .options(joinedload(WBUserCabinet.wb_cabinet))
                .where(WBUserCabinet.user_id == user_id)
            )
            result = await self._session.execute(stmt)
            cabinets = result.scalars().unique().all()
        except Exception as exc:
            raise McpStorageError("postgresql unavailable") from exc
        grants: list[ShopGrant] = []
        for cabinet in cabinets:
            wb_cabinet = cabinet.wb_cabinet
            active = bool(wb_cabinet.active) if wb_cabinet.active is not None else False
            grants.append(
                ShopGrant(
                    shop_id=str(wb_cabinet.shop_id),
                    name=cabinet.name,
                    active=active,
                )
            )
        return grants


def require_shop(grants: list[ShopGrant], shop_id: object) -> ShopGrant:
    """Найти точное строковое совпадение shop_id.

    Raises:
        McpError: аргумент не строка или связи нет (``SHOP_NOT_GRANTED``).
    """
    if not isinstance(shop_id, str) or not shop_id.strip():
        raise McpError("INVALID_ARGUMENT", "shop_id must be a string")
    for grant in grants:
        if grant.shop_id == shop_id:
            return grant
    raise McpError("SHOP_NOT_GRANTED", "shop is not granted")
