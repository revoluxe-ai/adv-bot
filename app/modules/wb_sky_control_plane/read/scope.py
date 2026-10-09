"""Resolve canonical shop_id scope to internal wb_cabinet_id."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.wb_sky_control_plane.models.changeset import LogicalScopeV1


async def resolve_wb_cabinet_id(
    session: AsyncSession,
    scope: LogicalScopeV1,
) -> int | None:
    """Map external shop_id to internal WBCabinet.id (infrastructure-only)."""
    if scope.provider != "wildberries":
        return None
    result = await session.execute(
        select(WBCabinet.id).where(WBCabinet.shop_id == scope.shop_id)
    )
    return result.scalar_one_or_none()
