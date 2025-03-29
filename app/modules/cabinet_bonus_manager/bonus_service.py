"""
Сервис для управления бонусами кабинетов.
Позволяет администраторам пополнять, убирать и обнулять бонусы кабинетов по shop_id.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.utils.db.session_maker import get_async_session_maker as sm
from app.modules.common_slaves.wildberries.models import WBCabinet, WBBonusPayment


async def add_bonus(shop_id: str, amount: float, admin_user_id: int, description: str) -> bool:
    """
    Пополнить бонусы кабинета по shop_id
    
    Args:
        shop_id: Идентификатор магазина
        amount: Сумма бонусов для добавления (положительное число)
        admin_user_id: ID администратора, выполняющего операцию
        description: Описание операции
        
    Returns:
        bool: True если операция успешна, False если кабинет не найден
    """
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")
        
    async with sm(read_only=False) as session:
        async with session.begin():
            cabinet = await _get_cabinet_by_shop_id(session, shop_id)
            if not cabinet:
                return False
                
            # Создаем запись о начислении бонусов
            bonus_payment = WBBonusPayment(
                wb_cabinet_id=cabinet.id,
                amount=amount,
                operation_type="add",
                admin_user_id=admin_user_id,
                description=description or f"Пополнение бонусов администратором ID:{admin_user_id}"
            )
            session.add(bonus_payment)
            
            # Больше не нужно изменять поле bonus напрямую, так как
            # calculated_bonus учитывает как исходное значение, так и все транзакции
            
            return True

async def subtract_bonus(shop_id: str, amount: float, admin_user_id: int, description: str = None) -> bool:
    """
    Снять бонусы с кабинета по shop_id
    
    Args:
        shop_id: Идентификатор магазина
        amount: Сумма бонусов для снятия (положительное число)
        admin_user_id: ID администратора, выполняющего операцию
        description: Описание операции
        
    Returns:
        bool: True если операция успешна, False если кабинет не найден или недостаточно бонусов
    """
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")
        
    async with sm(read_only=False) as session:
        async with session.begin():
            cabinet: WBCabinet = await _get_cabinet_by_shop_id(session, shop_id)
            if not cabinet:
                return False
            
            # Проверяем расчетный баланс бонусов
            calculated_bonus = cabinet.calculated_bonus
            if calculated_bonus < amount:
                return False
                
            # Создаем запись о снятии бонусов
            bonus_payment = WBBonusPayment(
                wb_cabinet_id=cabinet.id,
                amount=-amount,  # Отрицательная сумма для снятия
                operation_type="subtract",
                admin_user_id=admin_user_id,
                description=description or f"Снятие бонусов администратором ID:{admin_user_id}"
            )
            session.add(bonus_payment)
            
            # Больше не нужно изменять поле bonus напрямую
            
            return True

async def reset_bonus(shop_id: str, admin_user_id: int, description: str = None) -> bool:
    """
    Обнулить бонусы кабинета по shop_id
    
    Args:
        shop_id: Идентификатор магазина
        admin_user_id: ID администратора, выполняющего операцию
        description: Описание операции
        
    Returns:
        bool: True если операция успешна, False если кабинет не найден
    """
    async with sm(read_only=False) as session:
        async with session.begin():
            cabinet = await _get_cabinet_by_shop_id(session, shop_id)
            if not cabinet:
                return False
                
            # Проверяем расчетный баланс бонусов
            calculated_bonus = cabinet.calculated_bonus
            if calculated_bonus <= 0:
                return True
                
            # Создаем запись об обнулении бонусов с отрицательной суммой, равной текущему расчетному бонусу
            bonus_payment = WBBonusPayment(
                wb_cabinet_id=cabinet.id,
                amount=-calculated_bonus,  # Отрицательная сумма для обнуления
                operation_type="reset",
                admin_user_id=admin_user_id,
                description=description or f"Обнуление бонусов администратором ID:{admin_user_id}"
            )
            session.add(bonus_payment)
            
            # Больше не нужно изменять поле bonus напрямую
            
            return True

async def get_wb_cabinet(shop_id: str) -> WBCabinet:
    """
    Получить кабинет по shop_id с информацией о балансе и бонусах

    Args:
        shop_id: Идентификатор магазина

    Returns:
        WBCabinet: Объект кабинета с балансом и бонусами или None, если не найден
    """
    async with sm() as session:
        # Используем selectinload для предварительной загрузки bonus_payments,
        # чтобы избежать ошибки DetachedInstanceError
        stmt = select(WBCabinet).where(WBCabinet.shop_id == shop_id).options(
            selectinload(WBCabinet.bonus_payments),
            selectinload(WBCabinet.balance_payments)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()




async def _get_cabinet_by_shop_id(session: AsyncSession, shop_id: str) -> WBCabinet:
    """
    Получить кабинет по shop_id
    
    Args:
        session: Сессия SQLAlchemy
        shop_id: Идентификатор магазина
        
    Returns:
        WBCabinet: Объект кабинета или None, если не найден
    """
    # Также используем selectinload для _get_cabinet_by_shop_id
    stmt = select(WBCabinet).where(WBCabinet.shop_id == shop_id).options(
        selectinload(WBCabinet.bonus_payments),
        selectinload(WBCabinet.balance_payments)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() 