from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker


async def get_wb_user_cabinet_id_or_none(
    user_telegram_id: int, wb_cabinet_id: int
) -> int | None:
    async with get_async_session_maker() as session:
        stmt = (
            select(WBUserCabinet)
            .join(User, User.id == WBUserCabinet.user_id)
            .join(WBCabinet, WBCabinet.id == WBUserCabinet.wb_cabinet_id)
            .options(
                selectinload(WBUserCabinet.user),
                selectinload(WBUserCabinet.wb_cabinet).selectinload(
                    WBCabinet.adv_settings
                ),
            )
            .where(
                and_(
                    User.user_telegram_id == user_telegram_id,
                    WBCabinet.id == wb_cabinet_id,
                )
            )
        )
        result = await session.execute(stmt)
        wb_user_cabinet = result.scalar_one_or_none()
        return wb_user_cabinet.id if wb_user_cabinet else None


async def get_wb_user_cabinet_for_adv_and_telegram(
    session: AsyncSession,
    adv_setting: AdvSetting,
    user_telegram_id: int,
) -> WBUserCabinet | None:
    """Найти WBUserCabinet текущего Telegram-пользователя для кабинета кампании."""
    stmt = (
        select(WBUserCabinet)
        .join(User, User.id == WBUserCabinet.user_id)
        .where(User.user_telegram_id == user_telegram_id)
        .where(WBUserCabinet.wb_cabinet_id == adv_setting.wb_cabinet_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
