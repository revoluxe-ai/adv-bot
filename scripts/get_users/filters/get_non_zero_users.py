from typing import AsyncGenerator, Coroutine, Callable

from app.modules.balance_manager.balance_service import get_cabinet_balance
from app.utils.db.models import User


async def get_non_zero_users(get_users: AsyncGenerator[User, None],
                             max_balance: int = 200

                             ) -> AsyncGenerator[User, None]:
    async for user in get_users:
        wb_user_cabinets = user.wb_user_cabinets
        for wb_user_cabinet in wb_user_cabinets:
            wb_cabinet = wb_user_cabinet.wb_cabinet
            balance = wb_cabinet.balance
            bonus = wb_cabinet.bonus
            sum_balance = balance + bonus
            if sum_balance != 0 and sum_balance < max_balance:
                yield user



