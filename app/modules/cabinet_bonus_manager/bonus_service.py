"""
Сервис для управления бонусами кабинетов.
Позволяет администраторам пополнять, убирать и обнулять бонусы кабинетов по shop_id.
"""

from sqlalchemy import Result, select
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import WBBonusPayment, WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm


async def get_cabinet_by_id(cabinet_id: int) -> WBCabinet:
    """
    Получить кабинет по ID с информацией о балансе и бонусах

    Args:
        cabinet_id: ID кабинета

    Returns:
        WBCabinet: Объект кабинета с балансом и бонусами или None, если не найден
    """
    async with sm() as session:
        stmt = (
            select(WBCabinet)
            .where(WBCabinet.id == cabinet_id)
            .options(
                selectinload(WBCabinet.bonus_payments),
                selectinload(WBCabinet.balance_payments),
            )
        )
        result: Result[tuple[WBCabinet]] = await session.execute(stmt)
        return result.scalar_one_or_none()


async def add_bonus(
    wb_cabinet_original_id: int, amount: float, admin_user_id: int, description: str
) -> bool:
    """
    Пополнить бонусы кабинета по ID

    Args:
        wb_cabinet_original_id: ID кабинета
        amount: Сумма бонусов для добавления (положительное число)
        admin_user_id: ID администратора, выполняющего операцию
        description: Описание операции

    Returns:
        bool: True если операция успешна, False если кабинет не найден
    """
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")

    async with sm(read_only=False) as session:
        try:
            await session.begin()
            cabinet = await session.get(WBCabinet, wb_cabinet_original_id)
            if not cabinet:
                return False

            # Создаем запись о начислении бонусов
            bonus_payment = WBBonusPayment(
                wb_cabinet_id=cabinet.id,
                amount=amount,
                operation_type="add",
                admin_user_id=admin_user_id,
                description=description
                or f"Пополнение бонусов администратором ID:{admin_user_id}",
            )
            session.add(bonus_payment)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            raise


async def subtract_bonus(
    cabinet_id: int, amount: float, admin_user_id: int, description: str | None = None
) -> bool:
    """
    Снять бонусы с кабинета по ID

    Args:
        cabinet_id: ID кабинета
        amount: Сумма бонусов для снятия (положительное число)
        admin_user_id: ID администратора, выполняющего операцию
        description: Описание операции

    Returns:
        bool: True если операция успешна, False если кабинет не найден или недостаточно бонусов
    """
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")
    wb_cabinet = await get_cabinet_by_id(cabinet_id)
    async with sm(read_only=False) as session:
        await session.begin()
        calculated_bonus = wb_cabinet.calculated_bonus
        if calculated_bonus < amount:
            raise ValueError("Недостаточно бонусов")
        # Создаем запись о снятии бонусов
        bonus_payment = WBBonusPayment(
            wb_cabinet_id=wb_cabinet.id,
            amount=-amount,  # Отрицательная сумма для снятия
            operation_type="subtract",
            admin_user_id=admin_user_id,
            description=description
            or f"Снятие бонусов администратором ID:{admin_user_id}",
        )
        session.add(bonus_payment)
        await session.commit()
        return True


async def reset_bonus(cabinet_id: int, admin_user_id: int, description: str) -> bool:
    """
    Обнулить бонусы кабинета по ID

    Args:
        cabinet_id: ID кабинета
        admin_user_id: ID администратора, выполняющего операцию
        description: Описание операции

    Returns:
        bool: True если операция успешна, False если кабинет не найден
    """
    cabinet = await get_cabinet_by_id(cabinet_id)
    async with sm(read_only=False) as session:
        try:
            await session.begin()
            if not cabinet:
                return False
            # Проверяем расчетный баланс бонусов
            calculated_bonus = cabinet.calculated_bonus
            if calculated_bonus <= 0:
                return True

            # Создаем запись об обнулении бонусов с отрицательной суммой, равной текущему расчетному бонусу
            bonus_payment = WBBonusPayment(
                wb_cabinet_id=cabinet.id,
                amount=-calculated_bonus,
                operation_type="reset",
                admin_user_id=admin_user_id,
                description=description
                or f"Обнуление бонусов администратором ID:{admin_user_id}",
            )
            session.add(bonus_payment)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            raise


async def get_wb_cabinet_by_shop_id(shop_id: str) -> WBCabinet:
    """
    Получить кабинет по shop_id с информацией о балансе и бонусах

    Args:
        shop_id: Идентификатор магазина

    Returns:
        WBCabinet: Объект кабинета с балансом и бонусами или None, если не найден
    """

    async with sm() as session:
        stmt = (
            select(WBCabinet)
            .where(WBCabinet.shop_id == shop_id)
            .options(
                selectinload(WBCabinet.bonus_payments),
                selectinload(WBCabinet.balance_payments),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
