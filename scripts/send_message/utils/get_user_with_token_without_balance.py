from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.balance_manager.balance_service import get_cabinet_balance
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm


async def iter_users_with_zero_or_negative_balance_without_active_advs(
    batch_size: int = 10,
) -> AsyncIterator[User]:
    """
    Yield `User` records whose telegram ID is set and who own at least one WB cabinet
    with no `AdvSetting.bot_active` campaigns and whose `get_cabinet_balance`
    (balance + bonus) is less than or equal to zero.
    """

    stmt = select(User).options(
        selectinload(User.wb_user_cabinets)
        .selectinload(WBUserCabinet.wb_cabinet)
        .selectinload(WBCabinet.adv_settings)
    )

    async with sm() as session:
        users = await session.stream(stmt)
        async for user in users.scalars().yield_per(batch_size):
            if not user.user_telegram_id:
                continue

            for link in user.wb_user_cabinets:
                cabinet = link.wb_cabinet
                if not cabinet:
                    continue

                active_adv_exists = any(
                    getattr(ad, "bot_active", False)
                    for ad in cabinet.adv_settings
                    if isinstance(ad, AdvSetting)
                )
                if active_adv_exists:
                    continue

                balance, bonus = await get_cabinet_balance(cabinet.id)
                total = balance + bonus
                if total <= 0:
                    yield user
                    break
