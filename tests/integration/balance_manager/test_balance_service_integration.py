"""Интеграционные тесты для balance_service с реальной БД."""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.balance_manager.balance_service import (
    add_balance,
    add_bonus,
    get_cabinet_balance,
    process_payment_with_bonus,
)
from app.modules.balance_manager.exceptions import (
    CabinetNotFoundError,
    InvalidAmountError,
    UserNotFoundError,
)
from app.modules.common_slaves.wildberries.models import (
    WBBalancePayment,
    WBBonusPayment,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User


pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


async def _create_test_user(session: AsyncSession, user_telegram_id: int = 12345) -> User:
    """Создает тестового пользователя."""
    user = User(user_telegram_id=user_telegram_id, username="test_user")
    session.add(user)
    await session.flush()
    # Сервисы balance_service используют собственные сессии, поэтому данные должны быть закоммичены.
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_add_balance_integration(
    async_session: AsyncSession, cabinet: WBCabinet, test_session_factory
):
    """Интеграционный тест: создание записи о пополнении баланса в БД."""
    user = await _create_test_user(async_session)

    amount = 1000.0
    description = "Тестовое пополнение"

    payment = await add_balance(
        user_id=user.id,
        cabinet_id=cabinet.id,
        amount=amount,
        description=description,
    )

    # Платёж создан в другой сессии -> проверяем через запрос в текущей
    assert payment.id is not None
    payment_db = (
        await async_session.execute(
            select(WBBalancePayment).where(WBBalancePayment.id == payment.id)
        )
    ).scalar_one()
    assert payment_db.amount == amount
    assert payment_db.description == description
    assert payment_db.wb_cabinet_id == cabinet.id

    # Проверяем рассчитанный баланс через сервис (он подгружает payments в своей сессии)
    balance, bonus = await get_cabinet_balance(cabinet.id)
    assert balance == amount
    assert bonus == 0.0


@pytest.mark.asyncio
async def test_add_bonus_integration(
    async_session: AsyncSession, cabinet: WBCabinet, test_session_factory
):
    """Интеграционный тест: создание записи о начислении бонусов в БД."""
    user = await _create_test_user(async_session)

    amount = 2000.0
    description = "Тестовый бонус"

    bonus_payment = await add_bonus(
        user_id=user.id,
        cabinet_id=cabinet.id,
        amount=amount,
        description=description,
    )

    assert bonus_payment.id is not None
    bonus_db = (
        await async_session.execute(
            select(WBBonusPayment).where(WBBonusPayment.id == bonus_payment.id)
        )
    ).scalar_one()
    assert bonus_db.amount == amount
    assert bonus_db.description == description
    assert bonus_db.wb_cabinet_id == cabinet.id
    assert bonus_db.operation_type == "add"

    balance, bonus = await get_cabinet_balance(cabinet.id)
    assert balance == 0.0
    assert bonus == amount


@pytest.mark.asyncio
async def test_process_payment_with_bonus_integration_200_percent(
    async_session: AsyncSession,
    cabinet: WBCabinet,
    test_session_factory,
):
    """Интеграционный тест: обработка платежа с начислением 200% бонуса."""
    user = await _create_test_user(async_session)

    amount = 1000.0
    bonus_percent = 200.0

    balance_payment, bonus_payment, returned_amount, returned_bonus_amount = (
        await process_payment_with_bonus(
            user_id=user.id,
            cabinet_id=cabinet.id,
            amount=amount,
            bonus_percent=bonus_percent,
            description="Интеграционный тест",
        )
    )

    # Проверяем возвращаемые значения
    assert returned_amount == amount
    assert returned_bonus_amount == amount * 2  # 2000

    # Проверяем, что платежи созданы в БД
    assert balance_payment.id is not None
    assert bonus_payment is not None
    assert bonus_payment.id is not None

    # Проверяем рассчитанные значения через сервис
    balance, bonus = await get_cabinet_balance(cabinet.id)
    assert balance == amount
    assert bonus == amount * 2

    # Проверяем записи в БД напрямую
    balance_payments_stmt = select(WBBalancePayment).where(
        WBBalancePayment.wb_cabinet_id == cabinet.id
    )
    balance_payments_result = await async_session.execute(balance_payments_stmt)
    balance_payments = balance_payments_result.scalars().all()
    assert len(balance_payments) == 1
    assert balance_payments[0].amount == amount

    bonus_payments_stmt = select(WBBonusPayment).where(
        WBBonusPayment.wb_cabinet_id == cabinet.id
    )
    bonus_payments_result = await async_session.execute(bonus_payments_stmt)
    bonus_payments = bonus_payments_result.scalars().all()
    assert len(bonus_payments) == 1
    assert bonus_payments[0].amount == amount * 2


@pytest.mark.asyncio
async def test_process_payment_with_bonus_integration_zero_percent(
    async_session: AsyncSession,
    cabinet: WBCabinet,
    test_session_factory,
):
    """Интеграционный тест: обработка платежа без бонуса."""
    user = await _create_test_user(async_session)

    amount = 1000.0
    bonus_percent = 0.0

    balance_payment, bonus_payment, returned_amount, returned_bonus_amount = (
        await process_payment_with_bonus(
            user_id=user.id,
            cabinet_id=cabinet.id,
            amount=amount,
            bonus_percent=bonus_percent,
        )
    )

    assert returned_amount == amount
    assert returned_bonus_amount == 0.0
    assert bonus_payment is None

    balance, bonus = await get_cabinet_balance(cabinet.id)
    assert balance == amount
    assert bonus == 0.0

    # Проверяем, что бонусов нет в БД
    bonus_payments_stmt = select(WBBonusPayment).where(
        WBBonusPayment.wb_cabinet_id == cabinet.id
    )
    bonus_payments_result = await async_session.execute(bonus_payments_stmt)
    bonus_payments = bonus_payments_result.scalars().all()
    assert len(bonus_payments) == 0


@pytest.mark.asyncio
async def test_multiple_payments_accumulate_integration(
    async_session: AsyncSession, cabinet: WBCabinet, test_session_factory
):
    """Интеграционный тест: несколько платежей накапливаются."""
    user = await _create_test_user(async_session)

    # Первое пополнение
    await process_payment_with_bonus(
        user_id=user.id,
        cabinet_id=cabinet.id,
        amount=1000.0,
        bonus_percent=200.0,
    )
    balance, bonus = await get_cabinet_balance(cabinet.id)
    assert balance == 1000.0
    assert bonus == 2000.0

    # Второе пополнение
    await process_payment_with_bonus(
        user_id=user.id,
        cabinet_id=cabinet.id,
        amount=500.0,
        bonus_percent=200.0,
    )
    balance, bonus = await get_cabinet_balance(cabinet.id)
    assert balance == 1500.0  # 1000 + 500
    assert bonus == 3000.0  # 2000 + 1000

    # Проверяем количество записей в БД
    balance_payments_stmt = select(WBBalancePayment).where(
        WBBalancePayment.wb_cabinet_id == cabinet.id
    )
    balance_payments_result = await async_session.execute(balance_payments_stmt)
    balance_payments = balance_payments_result.scalars().all()
    assert len(balance_payments) == 2

    bonus_payments_stmt = select(WBBonusPayment).where(
        WBBonusPayment.wb_cabinet_id == cabinet.id
    )
    bonus_payments_result = await async_session.execute(bonus_payments_stmt)
    bonus_payments = bonus_payments_result.scalars().all()
    assert len(bonus_payments) == 2


@pytest.mark.asyncio
async def test_get_cabinet_balance_integration(
    async_session: AsyncSession, cabinet: WBCabinet, test_session_factory
):
    """Интеграционный тест: получение баланса и бонусов кабинета."""
    user = await _create_test_user(async_session)

    # Создаем несколько платежей
    await add_balance(user.id, cabinet.id, 1000.0, "Пополнение 1")
    await add_balance(user.id, cabinet.id, 500.0, "Пополнение 2")
    await add_bonus(user.id, cabinet.id, 2000.0, "Бонус 1")
    await add_bonus(user.id, cabinet.id, 1000.0, "Бонус 2")

    balance, bonus = await get_cabinet_balance(cabinet.id)

    assert balance == 1500.0  # 1000 + 500
    assert bonus == 3000.0  # 2000 + 1000


@pytest.mark.asyncio
async def test_add_balance_user_not_found_integration(
    async_session: AsyncSession, cabinet: WBCabinet, test_session_factory
):
    """Интеграционный тест: ошибка при отсутствии пользователя."""
    with pytest.raises(UserNotFoundError):
        await add_balance(
            user_id=99999,  # Несуществующий пользователь
            cabinet_id=cabinet.id,
            amount=1000.0,
        )


@pytest.mark.asyncio
async def test_add_balance_cabinet_not_found_integration(
    async_session: AsyncSession, test_session_factory
):
    """Интеграционный тест: ошибка при отсутствии кабинета."""
    user = await _create_test_user(async_session)

    with pytest.raises(CabinetNotFoundError):
        await add_balance(
            user_id=user.id,
            cabinet_id=99999,  # Несуществующий кабинет
            amount=1000.0,
        )


@pytest.mark.asyncio
async def test_process_payment_with_bonus_validation_integration(
    async_session: AsyncSession,
    cabinet: WBCabinet,
    test_session_factory,
):
    """Интеграционный тест: валидация в process_payment_with_bonus."""
    user = await _create_test_user(async_session)

    # Отрицательная сумма
    with pytest.raises(InvalidAmountError, match="Сумма пополнения должна быть положительной"):
        await process_payment_with_bonus(
            user_id=user.id,
            cabinet_id=cabinet.id,
            amount=-100.0,
            bonus_percent=200.0,
        )

    # Нулевая сумма
    with pytest.raises(InvalidAmountError, match="Сумма пополнения должна быть положительной"):
        await process_payment_with_bonus(
            user_id=user.id,
            cabinet_id=cabinet.id,
            amount=0.0,
            bonus_percent=200.0,
        )

    # Отрицательный процент
    with pytest.raises(InvalidAmountError, match="Процент бонуса не может быть отрицательным"):
        await process_payment_with_bonus(
            user_id=user.id,
            cabinet_id=cabinet.id,
            amount=1000.0,
            bonus_percent=-10.0,
        )


@pytest.mark.asyncio
async def test_cabinet_initial_balance_integration(
    async_session: AsyncSession, cabinet: WBCabinet, test_session_factory
):
    """Интеграционный тест: начальный баланс кабинета учитывается."""
    user = await _create_test_user(async_session)

    # Устанавливаем начальный баланс
    cabinet.balance = 500.0
    cabinet.bonus = 1000.0
    await async_session.flush()
    await async_session.commit()

    # Добавляем платеж
    await add_balance(user.id, cabinet.id, 1000.0, "Пополнение")
    balance, bonus = await get_cabinet_balance(cabinet.id)
    assert balance == 1500.0  # 500 (начальный) + 1000 (пополнение)
    assert bonus == 1000.0  # Только начальный бонус


@pytest.mark.asyncio
async def test_bonus_description_format_integration(
    async_session: AsyncSession, cabinet: WBCabinet, test_session_factory
):
    """Интеграционный тест: формат описания бонуса в БД."""
    user = await _create_test_user(async_session)

    bonus_percent = 200.0
    balance_payment, bonus_payment, returned_amount, returned_bonus_amount = (
        await process_payment_with_bonus(
            user_id=user.id,
            cabinet_id=cabinet.id,
            amount=1000.0,
            bonus_percent=bonus_percent,
        )
    )

    # Проверяем описание бонуса через возвращаемое значение (более надежно)
    assert bonus_payment is not None
    assert bonus_payment.description == f"Бонус {bonus_percent}% при пополнении баланса"

    # Проверяем в БД через отдельную сессию
    async with test_session_factory() as check_session:
        bonus_payments_stmt = select(WBBonusPayment).where(
            WBBonusPayment.wb_cabinet_id == cabinet.id
        )
        bonus_payments_result = await check_session.execute(bonus_payments_stmt)
        bonus_payments = bonus_payments_result.scalars().all()
        assert len(bonus_payments) == 1
        assert bonus_payments[0].description == f"Бонус {bonus_percent}% при пополнении баланса"


@pytest.mark.asyncio
async def test_fractional_amounts_integration(
    async_session: AsyncSession, cabinet: WBCabinet, test_session_factory
):
    """Интеграционный тест: работа с дробными суммами."""
    user = await _create_test_user(async_session)

    amount = 333.33
    bonus_percent = 200.0

    balance_payment, bonus_payment, returned_amount, returned_bonus_amount = (
        await process_payment_with_bonus(
            user_id=user.id,
            cabinet_id=cabinet.id,
            amount=amount,
            bonus_percent=bonus_percent,
        )
    )

    assert abs(returned_amount - amount) < 0.01
    expected_bonus = amount * 2  # 666.66
    assert abs(returned_bonus_amount - expected_bonus) < 0.01

    balance, bonus = await get_cabinet_balance(cabinet.id)
    assert abs(balance - amount) < 0.01
    assert abs(bonus - expected_bonus) < 0.01


