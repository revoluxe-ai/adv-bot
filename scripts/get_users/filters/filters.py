from typing import AsyncGenerator, Coroutine, Callable
from app.utils.db.session_maker import get_async_session_maker as sm
from app.modules.balance_manager.balance_service import get_cabinet_balance
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.utils.db.models import User
from scripts.users_csv_exporter.dto import UserDTO


def get_total_balance(wb_cabinet):
    total = wb_cabinet.calculated_balance + wb_cabinet.calculated_bonus
    return total


def get_total_active_advs(wb_cabinet: WBCabinet) -> int:
    advs = wb_cabinet.adv_settings
    active_advs = [adv for adv in advs if adv.bot_active]
    return len(active_advs)

pricer = Pricer()

async def get_price_for_day_for_shop(wb_cabinet: WBCabinet):
    async with sm(read_only=True) as session:
        price_for_shop_for_day = await pricer.get_price_for_day_for_shop(
            session, wb_cabinet.shop_id
        )
    return price_for_shop_for_day



async def get_user_with_near_payment(get_users: AsyncGenerator[User, None], max_for_payment: int):
    async for user in get_users:
        wb_user_cabinets = user.wb_user_cabinets
        for wb_user_cabinet in wb_user_cabinets:
            wb_cabinet = wb_user_cabinet.wb_cabinet
            balance = get_total_balance(wb_cabinet)
            price_for_day = await get_price_for_day_for_shop(wb_cabinet)
            if not price_for_day:
                continue
            exp_for_days = balance / price_for_day
            if exp_for_days <= max_for_payment:
                yield user
                break


async def get_users_by_telegram_id(get_users: AsyncGenerator[UserDTO, None],
                                    telegram_ids: list[int] | None) -> AsyncGenerator[UserDTO, None]:
     async for user in get_users:
         if user.telegram_id in telegram_ids:
             yield user




async def get_non_zero_users(get_users: AsyncGenerator[User, None],
                             max_balance: int = 200
                             ) -> AsyncGenerator[User, None]:
    async for user in get_users:
        break_flag = False
        total_balance = 0
        wb_user_cabinets = user.wb_user_cabinets
        for wb_user_cabinet in wb_user_cabinets:
            wb_cabinet = wb_user_cabinet.wb_cabinet
            balance = wb_cabinet.calculated_balance
            bonus = wb_cabinet.calculated_bonus
            sum_balance = balance + bonus
            if sum_balance > max_balance:
                break_flag = True
                break
            total_balance += sum_balance
        if not break_flag:
            if total_balance != 0:
                yield user


async def get_test_users(get_users: AsyncGenerator[UserDTO, None]) -> AsyncGenerator[UserDTO, None]:
    async for user in get_users:
        if user.telegram_id in [373435337]:
            yield user
