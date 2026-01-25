from typing import AsyncIterator

from scripts.get_users.get_users import get_users

from app.modules.balance_manager.balance_service import get_cabinet_balance
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.models import User


async def iter_users_with_zero_or_negative_balance_without_active_advs(
    batch_size,
) -> AsyncIterator[User]:
    """
    Yield `User` records whose telegram ID is set and for whom all tracked
    cabinets have a non-positive sum of `balance + bonus` and no active advs.
    """

    async for user in get_users(batch_size=batch_size):
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

            balance, bonus = await get_cabinet_balance(cabinet.id,
                                                       load_payments=False)
            total = balance + bonus
            if total <= 0:
                yield user
                break
