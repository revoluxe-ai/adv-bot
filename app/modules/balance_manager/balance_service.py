from datetime import datetime

from sqlalchemy.orm import selectinload

from app.modules.balance_manager.exceptions import (
    CabinetNotFoundError,
    InvalidAmountError,
    PaymentNotFoundError,
    UserNotFoundError,
)
from app.modules.common_slaves.wildberries.models import (
    WBBalancePayment,
    WBBonusPayment,
    WBCabinet,
)
from app.utils.db.models import Payment, User
from app.utils.db.session_maker import get_async_session_maker

# Алиас для получения сессии
sm = get_async_session_maker


async def add_balance(
    user_id: int, cabinet_id: int, amount: float, description: str | None = None
) -> WBBalancePayment:
    """
    Создает запись о пополнении баланса

    Args:
        user_id: ID пользователя в системе
        cabinet_id: ID кабинета WB
        amount: Сумма пополнения (должна быть положительной)
        description: Описание операции (опционально)

    Returns:
        WBBalancePayment: Созданная запись о пополнении

    Raises:
        UserNotFoundError: Если пользователь не найден
        CabinetNotFoundError: Если кабинет не найден
        InvalidAmountError: Если сумма меньше или равна нулю
    """
    if amount <= 0:
        raise InvalidAmountError("Сумма пополнения должна быть положительной")

    async with sm() as session:
        # Проверяем существование пользователя
        user = await session.get(User, user_id)
        if not user:
            raise UserNotFoundError(f"Пользователь с ID {user_id} не найден")

        # Проверяем существование кабинета
        cabinet = await session.get(WBCabinet, cabinet_id)
        if not cabinet:
            raise CabinetNotFoundError(f"Кабинет с ID {cabinet_id} не найден")

        # Формируем описание, если оно не предоставлено
        if not description:
            username = user.username or user.user_telegram_id
            description = f"Пополнение баланса пользователем {username}"

        # Создаем запись о пополнении баланса
        payment = WBBalancePayment(
            wb_cabinet_id=cabinet_id,
            amount=amount,
            description=description,
            transaction_date_time=datetime.now(),
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)

        return payment


async def add_bonus(
    user_id: int, cabinet_id: int, amount: float, description: str | None = None
) -> WBBonusPayment:
    """
    Создает запись о начислении бонусов

    Args:
        user_id: ID пользователя в системе
        cabinet_id: ID кабинета WB
        amount: Сумма бонусов (должна быть положительной)
        description: Описание операции (опционально)

    Returns:
        WBBonusPayment: Созданная запись о начислении бонусов

    Raises:
        UserNotFoundError: Если пользователь не найден
        CabinetNotFoundError: Если кабинет не найден
        InvalidAmountError: Если сумма меньше или равна нулю
    """
    if amount <= 0:
        raise InvalidAmountError("Сумма бонуса должна быть положительной")

    async with sm() as session:
        # Проверяем существование пользователя
        user = await session.get(User, user_id)
        if not user:
            raise UserNotFoundError(f"Пользователь с ID {user_id} не найден")

        # Проверяем существование кабинета
        cabinet = await session.get(WBCabinet, cabinet_id)
        if not cabinet:
            raise CabinetNotFoundError(f"Кабинет с ID {cabinet_id} не найден")

        # Формируем описание, если оно не предоставлено
        if not description:
            username = user.username or user.user_telegram_id
            description = f"Начисление бонусов пользователю {username}"

        # Создаем запись о начислении бонусов
        bonus_payment = WBBonusPayment(
            wb_cabinet_id=cabinet_id,
            amount=amount,
            description=description,
            transaction_date_time=datetime.now(),
            operation_type="add",
        )
        session.add(bonus_payment)
        await session.commit()
        await session.refresh(bonus_payment)

        return bonus_payment


async def get_cabinet_balance(cabinet_id: int) -> tuple[float, float]:
    """Получает текущий баланс и бонусы кабинета с учетом всех платежей"""
    async with sm() as session:
        cabinet = await session.get(
            WBCabinet,
            cabinet_id,
            options=[
                selectinload(WBCabinet.balance_payments),
                selectinload(WBCabinet.bonus_payments),
            ],
        )
        if not cabinet:
            raise CabinetNotFoundError(f"Кабинет с ID {cabinet_id} не найден")

        return cabinet.calculated_balance, cabinet.calculated_bonus


async def confirm_payment(
    user_id: int, payment_id: int, add_to_system_payments: bool = True
) -> tuple[WBBalancePayment, WBCabinet]:
    """
    Подтверждает платеж и регистрирует его в системе платежей

    Args:
        user_id: ID пользователя
        payment_id: ID платежа WBBalancePayment
        add_to_system_payments: Добавлять ли запись в таблицу Payment

    Returns:
        Tuple[WBBalancePayment, WBCabinet]: Подтвержденный платеж и кабинет

    Raises:
        UserNotFoundError: Если пользователь не найден
        PaymentNotFoundError: Если платеж не найден
    """
    async with sm() as session:
        # Проверяем существование пользователя
        user = await session.get(User, user_id)
        if not user:
            raise UserNotFoundError(f"Пользователь с ID {user_id} не найден")

        # Получаем платеж
        payment = await session.get(WBBalancePayment, payment_id)
        if not payment:
            raise PaymentNotFoundError(f"Платеж с ID {payment_id} не найден")

        # Получаем кабинет
        cabinet = await session.get(WBCabinet, payment.wb_cabinet_id)
        if not cabinet:
            raise CabinetNotFoundError(
                f"Кабинет с ID {payment.wb_cabinet_id} не найден"
            )

        # Если указано, создаем запись в общей таблице платежей
        if add_to_system_payments:
            system_payment = Payment(
                user=user,
                amount=payment.amount,
                target="balance",
            )
            session.add(system_payment)

        await session.commit()
        await session.refresh(payment)
        await session.refresh(cabinet)

        return payment, cabinet


async def process_payment_with_bonus(
    user_id: int,
    cabinet_id: int,
    amount: float,
    bonus_percent: float = 0.0,
    description: str | None = None,
) -> tuple[WBBalancePayment, WBBonusPayment | None, float, float]:
    """
    Комплексная функция для обработки платежа с начислением бонуса

    Args:
        user_id: ID пользователя
        cabinet_id: ID кабинета WB
        amount: Сумма пополнения
        bonus_percent: Процент бонуса (от 0 до 100)
        description: Описание операции

    Returns:
        Tuple: (платеж_баланса, платеж_бонуса, сумма_баланса, сумма_бонуса)

    Raises:
        UserNotFoundError: Если пользователь не найден
        CabinetNotFoundError: Если кабинет не найден
        InvalidAmountError: Если сумма меньше или равна нулю
    """
    if amount <= 0:
        raise InvalidAmountError("Сумма пополнения должна быть положительной")

    bonus_amount = amount * (bonus_percent / 100) if bonus_percent > 0 else 0

    # Создаем запись о пополнении баланса
    balance_payment = await add_balance(user_id, cabinet_id, amount, description)

    # Если есть бонус, создаем запись о бонусе
    bonus_payment = None
    if bonus_amount > 0:
        bonus_payment = await add_bonus(
            user_id,
            cabinet_id,
            bonus_amount,
            f"Бонус {bonus_percent}% при пополнении баланса",
        )

    return balance_payment, bonus_payment, amount, bonus_amount
