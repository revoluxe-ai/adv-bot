from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

from app.modules.balance_manager.exceptions import (
    CabinetNotFoundError,
    InsufficientBalanceError,
    InvalidAmountError,
    UserNotFoundError,
)
from app.modules.common_slaves.wildberries.models import (
    WBBalancePayment,
    WBBonusPayment,
)

from app.utils.db.models import User, UserBalancePayment, UserBonusPayment
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


# TODO Проверить если нет и добавить ping токенов на все нужные права


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


def _user_balance_total(payments: list[UserBalancePayment]) -> float:
    """Сумма amount по записям личного баланса пользователя."""
    return sum(float(p.amount) for p in payments)


def _user_bonus_total(payments: list[UserBonusPayment]) -> float:
    """Сумма amount по записям бонусов пользователя."""
    return sum(float(p.amount) for p in payments)


async def transfer_user_balance_to_cabinet(
    user_telegram_id: int,
    cabinet_id: int,
    amount: float,
    description: str | None = None,
) -> tuple[UserBalancePayment | None, UserBonusPayment | None, WBBalancePayment]:
    """
    Переводит средства с личного баланса и бонусов пользователя на баланс кабинета.
    Сначала списывается с баланса, остаток — с бонусов. Выполняется в одной транзакции.

    Args:
        user_telegram_id: Telegram ID пользователя
        cabinet_id: ID кабинета WB
        amount: Сумма перевода (должна быть положительной)
        description: Описание операции (опционально)

    Returns:
        (UserBalancePayment | None, UserBonusPayment | None, WBBalancePayment) —
        записи списания с баланса и бонусов (None если списание по этому типу не было),
        запись зачисления на кабинет

    Raises:
        UserNotFoundError: Если пользователь не найден
        CabinetNotFoundError: Если кабинет не найден
        InvalidAmountError: Если сумма <= 0
        InsufficientBalanceError: Если на личном балансе и бонусах недостаточно средств
    """
    if amount <= 0:
        raise InvalidAmountError("Сумма перевода должна быть положительной")

    async with sm() as session:
        stmt = (
            select(User)
            .where(User.user_telegram_id == user_telegram_id)
            .options(
                selectinload(User.user_balance_payments),
                selectinload(User.user_bonus_payments),
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(
                f"Пользователь с telegram_id {user_telegram_id} не найден"
            )

        cabinet = await session.get(WBCabinet, cabinet_id)
        if not cabinet:
            raise CabinetNotFoundError(f"Кабинет с ID {cabinet_id} не найден")

        balance_available = _user_balance_total(user.user_balance_payments)
        bonus_available = _user_bonus_total(user.user_bonus_payments)
        total_available = balance_available + bonus_available
        if total_available < amount:
            raise InsufficientBalanceError(
                f"Недостаточно средств на личном балансе и бонусах: "
                f"доступно {total_available:.2f}, требуется {amount:.2f}"
            )

        if not description:
            description = (
                f"Перевод на кабинет (cabinet_id={cabinet_id}, tg={user_telegram_id})"
            )

        debit_from_balance = min(amount, balance_available)
        debit_from_bonus = amount - debit_from_balance

        user_balance_payment: UserBalancePayment | None = None
        if debit_from_balance > 0:
            user_balance_payment = UserBalancePayment(
                user_id=user.id,
                amount=-debit_from_balance,
                description=description,
                transaction_date_time=datetime.now(),
                operation_type="transfer_to_cabinet",
            )
            session.add(user_balance_payment)

        user_bonus_payment: UserBonusPayment | None = None
        if debit_from_bonus > 0:
            user_bonus_payment = UserBonusPayment(
                user_id=user.id,
                amount=-debit_from_bonus,
                description=description,
                transaction_date_time=datetime.now(),
                operation_type="transfer_to_cabinet",
                admin_user_id=None,
            )
            session.add(user_bonus_payment)

        cabinet_payment = WBBalancePayment(
            wb_cabinet_id=cabinet_id,
            amount=amount,
            description=description,
            transaction_date_time=datetime.now(),
            operation_type="add",
        )
        session.add(cabinet_payment)

        await session.commit()
        if user_balance_payment is not None:
            await session.refresh(user_balance_payment)
        if user_bonus_payment is not None:
            await session.refresh(user_bonus_payment)
        await session.refresh(cabinet_payment)

        return user_balance_payment, user_bonus_payment, cabinet_payment


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
        bonus_percent: Процент бонуса (может быть больше 100, например 200 для двойного бонуса)
        description: Описание операции

    Returns:
        Tuple: (платеж_баланса, платеж_бонуса, сумма_баланса, сумма_бонуса)

    Raises:
        UserNotFoundError: Если пользователь не найден
        CabinetNotFoundError: Если кабинет не найден
        InvalidAmountError: Если сумма меньше или равна нулю, или процент бонуса отрицательный
    """
    if amount <= 0:
        raise InvalidAmountError("Сумма пополнения должна быть положительной")

    if bonus_percent < 0:
        raise InvalidAmountError("Процент бонуса не может быть отрицательным")

    # TODO(money): суммы/баланс должны быть Decimal (денежные расчеты),
    # float здесь временно; допускаем погрешность в тестах только как временную меру.
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
