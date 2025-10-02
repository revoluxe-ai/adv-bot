from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker


async def get_wb_user_cabinet_id_or_none(user_telegram_id: int, wb_cabinet_id: int) -> int | None:
    async with get_async_session_maker() as session:
        stmt = (
            select(WBUserCabinet)
            .join(User, User.id == WBUserCabinet.user_id)
            .join(WBCabinet, WBCabinet.id == WBUserCabinet.wb_cabinet_id)
            .options(
                selectinload(WBUserCabinet.user),
                selectinload(WBUserCabinet.wb_cabinet).selectinload(WBCabinet.adv_settings),
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
