import dotenv
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import (
    WBBalancePayment,
    WBBonusPayment,
    WBCabinet,
)
from app_old.utils.db.session_maker import get_async_session_maker as sm

dotenv.load_dotenv()

shop_id = ...
add_balance = ...
add_bonus = ...


async def add_balance_and_bonus():
    async with sm(read_only=False) as session:
        stmt = select(WBCabinet).where(WBCabinet.shop_id == shop_id)
        result = await session.execute(stmt)
        wb_cabinet = result.scalar_one_or_none()
        if not wb_cabinet:
            print(f"Кабинет с shop_id {shop_id} не найден")
            return

        # Создаем запись о пополнении баланса, если он добавляется
        if add_balance > 0:
            balance_payment = WBBalancePayment(
                wb_cabinet_id=wb_cabinet.id,
                amount=add_balance,
                description="Пополнение баланса через скрипт add_to_shop_balance.py",
            )
            session.add(balance_payment)

        # Создаем запись о начислении бонусов, если они добавляются
        if add_bonus > 0:
            bonus_payment = WBBonusPayment(
                wb_cabinet_id=wb_cabinet.id,
                amount=add_bonus,
                description="Добавление бонусов через скрипт add_to_shop_balance.py",
            )
            session.add(bonus_payment)

        await session.commit()
        # Получаем обновленные значения
        calculated_balance = wb_cabinet.calculated_balance
        calculated_bonus = wb_cabinet.calculated_bonus

        print(
            f"Баланс кабинета {shop_id} увеличен: {add_balance} (новый расчетный баланс: {calculated_balance})"
        )
        print(
            f"Бонусы кабинета {shop_id} увеличены: {add_bonus} (новый расчетный бонус: {calculated_bonus})"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(add_balance_and_bonus())
