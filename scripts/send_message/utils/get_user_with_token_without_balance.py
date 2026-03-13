from typing import AsyncIterator

from scripts.get_users.get_users import get_users
from scripts.users_csv_exporter.dto import UserDTO


async def iter_users_with_zero_or_negative_balance_without_active_advs(
    batch_size: int,
) -> AsyncIterator[UserDTO]:
    """
    Yield `UserDTO` records whose telegram ID is set and for whom at least one
    cabinet has a non-positive balance+bonus and no active advs.
    """

    async for user in get_users(batch_size=batch_size):
        if not user.telegram_id:
            continue

        for cabinet in user.cabinets:
            if cabinet.has_active_campaign:
                continue
            if cabinet.balance_plus_bonus <= 0:
                yield user
                break
