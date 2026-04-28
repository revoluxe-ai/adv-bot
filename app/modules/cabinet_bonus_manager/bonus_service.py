"""
Сервис для управления бонусами кабинетов.
Позволяет администраторам пополнять, убирать и обнулять бонусы кабинетов по shop_id.
"""

from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

from sqlalchemy import Result, select
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import WBBalancePayment, WBBonusPayment

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
        result: Result[WBCabinet] = await session.execute(stmt)
        return result.scalar_one_or_none()


def _admin_desc_fallback(
    default: str, description: str | None, admin_user_id: int | None
) -> str:
    """Fallback для description: description или default с ID если есть."""
    if description:
        return description
    return (
        f"{default} ID:{admin_user_id}"
        if admin_user_id is not None
        else default
    )


async def add_bonus(
    wb_cabinet_original_id: int,
    amount: float,
    admin_user_id: int | None,
    description: str,
) -> bool:
    """
    Пополнить бонусы кабинета по ID

    Args:
        wb_cabinet_original_id: ID кабинета
        amount: Сумма бонусов для добавления (положительное число)
        admin_user_id: User.id администратора (внутренний PK), выполняющего операцию
        description: Описание операции (должно содержать tg админа для аудита)

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

            desc = _admin_desc_fallback(
                "Пополнение бонусов администратором.",
                description or None,
                admin_user_id,
            )
            bonus_payment = WBBonusPayment(
                wb_cabinet_id=cabinet.id,
                amount=amount,
                operation_type="add",
                admin_user_id=admin_user_id,
                description=desc,
            )
            session.add(bonus_payment)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            raise


async def add_balance(
    wb_cabinet_original_id: int,
    amount: float,
    admin_user_id: int | None,
    description: str | None = None,
) -> bool:
    """Пополнить баланс кабинета по ID."""
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")

    async with sm(read_only=False) as session:
        try:
            await session.begin()
            cabinet = await session.get(WBCabinet, wb_cabinet_original_id)
            if not cabinet:
                return False

            desc = _admin_desc_fallback(
                "Пополнение баланса администратором.",
                description,
                admin_user_id,
            )
            balance_payment = WBBalancePayment(
                wb_cabinet_id=cabinet.id,
                amount=amount,
                operation_type="add",
                description=desc,
            )
            session.add(balance_payment)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            raise


async def subtract_bonus(
    cabinet_id: int,
    amount: float,
    admin_user_id: int | None,
    description: str | None = None,
) -> bool:
    """
    Снять бонусы с кабинета по ID

    Args:
        cabinet_id: ID кабинета
        amount: Сумма бонусов для снятия (положительное число)
        admin_user_id: User.id администратора (внутренний PK), выполняющего операцию
        description: Описание операции (должно содержать tg админа для аудита)

    Returns:
        bool: True если операция успешна, False если кабинет не найден или недостаточно бонусов
    """
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")
    wb_cabinet = await get_cabinet_by_id(cabinet_id)
    desc = _admin_desc_fallback(
        "Снятие бонусов администратором.",
        description,
        admin_user_id,
    )
    async with sm(read_only=False) as session:
        await session.begin()
        calculated_bonus = wb_cabinet.calculated_bonus
        if calculated_bonus < amount:
            raise ValueError("Недостаточно бонусов")
        bonus_payment = WBBonusPayment(
            wb_cabinet_id=wb_cabinet.id,
            amount=-amount,
            operation_type="subtract",
            admin_user_id=admin_user_id,
            description=desc,
        )
        session.add(bonus_payment)
        await session.commit()
        return True


async def subtract_balance(
    cabinet_id: int,
    amount: float,
    admin_user_id: int | None,
    description: str | None = None,
) -> bool:
    """Снять средства с баланса кабинета по ID."""
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")
    wb_cabinet = await get_cabinet_by_id(cabinet_id)
    desc = _admin_desc_fallback(
        "Снятие баланса администратором.",
        description,
        admin_user_id,
    )
    async with sm(read_only=False) as session:
        await session.begin()
        calculated_balance = wb_cabinet.calculated_balance
        if calculated_balance < amount:
            raise ValueError("Недостаточно баланса")
        balance_payment = WBBalancePayment(
            wb_cabinet_id=wb_cabinet.id,
            amount=-amount,
            operation_type="subtract",
            description=desc,
        )
        session.add(balance_payment)
        await session.commit()
        return True


async def reset_bonus(
    cabinet_id: int, admin_user_id: int | None, description: str
) -> bool:
    """
    Обнулить бонусы кабинета по ID

    Args:
        cabinet_id: ID кабинета
        admin_user_id: User.id администратора (внутренний PK), выполняющего операцию
        description: Описание операции (должно содержать tg админа для аудита)

    Returns:
        bool: True если операция успешна, False если кабинет не найден
    """
    cabinet = await get_cabinet_by_id(cabinet_id)
    desc = _admin_desc_fallback(
        "Обнуление бонусов администратором.",
        description or None,
        admin_user_id,
    )
    async with sm(read_only=False) as session:
        try:
            await session.begin()
            if not cabinet:
                return False
            calculated_bonus = cabinet.calculated_bonus
            if calculated_bonus <= 0:
                return True

            bonus_payment = WBBonusPayment(
                wb_cabinet_id=cabinet.id,
                amount=-calculated_bonus,
                operation_type="reset",
                admin_user_id=admin_user_id,
                description=desc,
            )
            session.add(bonus_payment)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            raise


async def reset_balance(
    cabinet_id: int, admin_user_id: int | None, description: str | None = None
) -> bool:
    """Обнулить баланс кабинета по ID."""
    cabinet = await get_cabinet_by_id(cabinet_id)
    desc = _admin_desc_fallback(
        "Обнуление баланса администратором.",
        description,
        admin_user_id,
    )
    async with sm(read_only=False) as session:
        try:
            await session.begin()
            if not cabinet:
                return False
            calculated_balance = cabinet.calculated_balance
            if calculated_balance <= 0:
                return True

            balance_payment = WBBalancePayment(
                wb_cabinet_id=cabinet.id,
                amount=-calculated_balance,
                operation_type="reset",
                description=desc,
            )
            session.add(balance_payment)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            raise


async def subtract_total_with_bonus_priority(
    cabinet_id: int,
    amount: float,
    admin_user_id: int | None,
    description: str | None = None,
) -> tuple[bool, float, float]:
    """
    Списывает сумму с кабинета: сначала бонусы до 0, затем баланс.
    Уход в минус разрешен только для баланса.

    Returns:
        (success, bonus_spent, balance_spent)
    """
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")

    wb_cabinet = await get_cabinet_by_id(cabinet_id)
    if not wb_cabinet:
        return False, 0.0, 0.0

    bonus_available = max(0.0, float(wb_cabinet.calculated_bonus))

    bonus_spent = min(bonus_available, amount)
    balance_spent = amount - bonus_spent
    desc = _admin_desc_fallback(
        "Комбинированное списание (сначала бонусы, затем баланс) администратором.",
        description,
        admin_user_id,
    )

    async with sm(read_only=False) as session:
        try:
            await session.begin()
            if bonus_spent > 0:
                session.add(
                    WBBonusPayment(
                        wb_cabinet_id=wb_cabinet.id,
                        amount=-bonus_spent,
                        operation_type="subtract",
                        admin_user_id=admin_user_id,
                        description=desc,
                    )
                )
            if balance_spent > 0:
                session.add(
                    WBBalancePayment(
                        wb_cabinet_id=wb_cabinet.id,
                        amount=-balance_spent,
                        operation_type="subtract",
                        description=desc,
                    )
                )
            await session.commit()
            return True, bonus_spent, balance_spent
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
