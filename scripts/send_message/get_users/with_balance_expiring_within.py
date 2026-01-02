from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.utils.db.session_maker import get_async_session_maker as sm
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.models import User
from app.modules.balance_manager.balance_service import get_cabinet_balance

async def get_users_with_balance_expiring_within(days: int):
    pricer = Pricer()
    stmt = select(User).options(
        selectinload(User.wb_user_cabinets).selectinload(
            WBUserCabinet.wb_cabinet
        ).selectinload(WBCabinet.adv_settings)
    )
    async with sm() as session:
        users = await session.stream(stmt)
        async for user in users.scalars().yield_per(10):
            should_include_user = False
            wb_user_cabinets = user.wb_user_cabinets

            for wb_user_cabinet in wb_user_cabinets:
                wb_cabinet = wb_user_cabinet.wb_cabinet
                shop_id = wb_cabinet.shop_id

                # Проверяем наличие активных кампаний
                active_advs = [
                    adv for adv in wb_cabinet.adv_settings if adv.bot_active
                ]

                if not active_advs:
                    continue  # Нет активных кампаний, пропускаем кабинет

                # Получаем баланс и бонусы
                balance, bonus = await get_cabinet_balance (
                    wb_cabinet.id
                )
                total_money = balance + bonus

                # Получаем ежедневные расходы
                daily_tariff = await pricer.get_price_for_day_for_shop(
                    session, shop_id
                )

                # Рассчитываем дни до окончания баланса
                if daily_tariff > 0:
                    days_left = int(total_money / daily_tariff)
                    if 0 < days_left <= days:
                        should_include_user = True
                        break  # Достаточно одного подходящего кабинета

            if should_include_user:
                yield user