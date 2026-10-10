"""Проверка, что Telegram-пользователь владеет кабинетом. Только чтение PG."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.models import User


async def load_owned_cabinet(
    session: AsyncSession,
    *,
    wb_user_cabinet_id: int,
    telegram_user_id: int,
) -> WBUserCabinet | None:
    """Кабинет с wb_cabinet, если telegram id — владелец. Иначе None."""
    stmt = (
        select(WBUserCabinet)
        .join(WBUserCabinet.user)
        .join(WBUserCabinet.wb_cabinet)
        .options(selectinload(WBUserCabinet.wb_cabinet))
        .where(
            WBUserCabinet.id == wb_user_cabinet_id,
            User.user_telegram_id == telegram_user_id,
        )
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()
