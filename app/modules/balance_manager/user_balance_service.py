"""Сервис личного баланса и бонусов пользователя (по user_telegram_id)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.balance_manager.exceptions import InvalidAmountError, UserNotFoundError
from app.utils.db.models import User, UserBalancePayment, UserBonusPayment
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker


async def add_user_balance(
    user_telegram_id: int,
    amount: float,
    description: str | None = None,
) -> UserBalancePayment:
    """
    Создаёт запись о пополнении личного баланса пользователя.

    Args:
        user_telegram_id: Telegram ID пользователя
        amount: Сумма пополнения (должна быть положительной)
        description: Описание операции (опционально)

    Returns:
        UserBalancePayment: Созданная запись

    Raises:
        UserNotFoundError: Если пользователь не найден
        InvalidAmountError: Если сумма <= 0
    """
    if amount <= 0:
        raise InvalidAmountError("Сумма пополнения должна быть положительной")

    async with sm() as session:
        stmt = select(User).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(
                f"Пользователь с telegram_id {user_telegram_id} не найден"
            )

        if not description:
            description = f"Пополнение личного баланса (tg:{user_telegram_id})"

        payment = UserBalancePayment(
            user_id=user.id,
            amount=amount,
            description=description,
            transaction_date_time=datetime.now(),
            operation_type="add",
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment


async def add_user_bonus(
    user_telegram_id: int,
    amount: float,
    description: str | None = None,
) -> UserBonusPayment:
    """
    Создаёт запись о начислении бонусов пользователю.

    Args:
        user_telegram_id: Telegram ID пользователя
        amount: Сумма бонусов (должна быть положительной)
        description: Описание операции (опционально)

    Returns:
        UserBonusPayment: Созданная запись

    Raises:
        UserNotFoundError: Если пользователь не найден
        InvalidAmountError: Если сумма <= 0
    """
    if amount <= 0:
        raise InvalidAmountError("Сумма бонуса должна быть положительной")

    async with sm() as session:
        stmt = select(User).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(
                f"Пользователь с telegram_id {user_telegram_id} не найден"
            )

        if not description:
            description = f"Бонус при пополнении личного баланса (tg:{user_telegram_id})"

        payment = UserBonusPayment(
            user_id=user.id,
            amount=amount,
            description=description,
            transaction_date_time=datetime.now(),
            operation_type="add",
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment


def _calculated_balance(payments: list[UserBalancePayment]) -> float:
    """Сумма amount по записям баланса."""
    return sum(float(p.amount) for p in payments)


def _calculated_bonus(payments: list[UserBonusPayment]) -> float:
    """Сумма amount по записям бонусов."""
    return sum(float(p.amount) for p in payments)


async def get_user_balance(user_telegram_id: int) -> tuple[float, float]:
    """
    Возвращает текущий баланс и бонусы пользователя (сумма по платежам).

    Args:
        user_telegram_id: Telegram ID пользователя

    Returns:
        (balance, bonus) — баланс и бонусы в рублях

    Raises:
        UserNotFoundError: Если пользователь не найден
    """
    async with sm() as session:
        stmt = (
            select(User)
            .where(User.user_telegram_id == user_telegram_id)
            .options(
                selectinload(User.user_balance_payments),
                selectinload(User.user_bonus_payments),
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
    if not user:
        raise UserNotFoundError(
            f"Пользователь с telegram_id {user_telegram_id} не найден"
        )
    balance = _calculated_balance(user.user_balance_payments)
    bonus = _calculated_bonus(user.user_bonus_payments)
    return balance, bonus


async def process_user_payment_with_bonus(
    user_telegram_id: int,
    amount: float,
    bonus_percent: float = 0.0,
    description: str | None = None,
) -> tuple[UserBalancePayment, UserBonusPayment | None, float, float]:
    """
    Обрабатывает пополнение личного баланса с начислением бонуса.

    Args:
        user_telegram_id: Telegram ID пользователя
        amount: Сумма пополнения
        bonus_percent: Процент бонуса (0 = без бонуса)
        description: Описание операции

    Returns:
        (balance_payment, bonus_payment_or_none, amount, bonus_amount)

    Raises:
        UserNotFoundError: Если пользователь не найден
        InvalidAmountError: Если сумма <= 0 или bonus_percent < 0
    """
    if amount <= 0:
        raise InvalidAmountError("Сумма пополнения должна быть положительной")
    if bonus_percent < 0:
        raise InvalidAmountError("Процент бонуса не может быть отрицательным")

    bonus_amount = amount * (bonus_percent / 100) if bonus_percent > 0 else 0.0

    balance_payment = await add_user_balance(
        user_telegram_id, amount, description or "Пополнение личного баланса через Telegram"
    )

    bonus_payment: UserBonusPayment | None = None
    if bonus_amount > 0:
        bonus_payment = await add_user_bonus(
            user_telegram_id,
            bonus_amount,
            f"Бонус {bonus_percent}% при пополнении личного баланса",
        )

    return balance_payment, bonus_payment, amount, bonus_amount
