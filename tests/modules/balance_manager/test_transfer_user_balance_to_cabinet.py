"""Unit-тесты для transfer_user_balance_to_cabinet."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.balance_manager.balance_service import transfer_user_balance_to_cabinet
from app.modules.balance_manager.exceptions import (
    CabinetNotFoundError,
    InsufficientBalanceError,
    InvalidAmountError,
    UserNotFoundError,
)
from app.utils.db.models import UserBalancePayment


pytestmark = pytest.mark.asyncio


def _make_user_with_balance(balance: float, user_id: int = 1):
    """User с заданной суммой по user_balance_payments."""
    user = MagicMock()
    user.id = user_id
    user.user_telegram_id = 12345
    pay = MagicMock(spec=UserBalancePayment)
    pay.amount = balance
    user.user_balance_payments = [pay]
    return user


def _make_session_mock(user=None, cabinet=MagicMock(), add_calls=None):
    if add_calls is None:
        add_calls = []

    async def execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        return result

    async def get(model, pk):
        name = getattr(model, "__name__", "") or str(model)
        if "User" in name:
            return user
        if "WBCabinet" in name:
            return cabinet
        return None

    session = AsyncMock()
    session.execute = execute
    session.get = get
    session.add = lambda obj: add_calls.append(obj)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session, add_calls


def _make_async_cm(session):
    """Возвращает объект, который при использовании в async with отдаёт session."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


@patch("app.modules.balance_manager.balance_service.sm")
async def test_transfer_user_balance_to_cabinet_success(mock_sm):
    """Успешный перевод: достаточный баланс, создаются обе записи."""
    user = _make_user_with_balance(1000.0)
    cabinet = MagicMock()
    add_calls = []
    session, _ = _make_session_mock(user=user, cabinet=cabinet, add_calls=add_calls)
    mock_sm.return_value = _make_async_cm(session)

    user_payment, cabinet_payment = await transfer_user_balance_to_cabinet(
        user_telegram_id=12345,
        cabinet_id=1,
        amount=100.0,
    )

    assert len(add_calls) == 2
    first, second = add_calls[0], add_calls[1]
    # UserBalancePayment: negative amount, operation_type transfer_to_cabinet
    if hasattr(first, "amount") and first.amount < 0:
        ubp, wbp = first, second
    else:
        wbp, ubp = first, second
    assert ubp.amount == -100.0
    assert ubp.operation_type == "transfer_to_cabinet"
    assert wbp.amount == 100.0
    assert wbp.wb_cabinet_id == 1
    session.commit.assert_awaited_once()


@patch("app.modules.balance_manager.balance_service.sm")
async def test_transfer_user_balance_to_cabinet_insufficient_balance(mock_sm):
    """Недостаточно средств на личном балансе -> InsufficientBalanceError."""
    user = _make_user_with_balance(50.0)
    cabinet = MagicMock()
    add_calls = []
    session, _ = _make_session_mock(user=user, cabinet=cabinet, add_calls=add_calls)
    mock_sm.return_value = _make_async_cm(session)

    with pytest.raises(InsufficientBalanceError, match="Недостаточно средств"):
        await transfer_user_balance_to_cabinet(
            user_telegram_id=12345,
            cabinet_id=1,
            amount=100.0,
        )

    assert len(add_calls) == 0
    session.commit.assert_not_awaited()


@patch("app.modules.balance_manager.balance_service.sm")
async def test_transfer_user_balance_to_cabinet_user_not_found(mock_sm):
    """Пользователь не найден -> UserNotFoundError."""
    session, add_calls = _make_session_mock(user=None, cabinet=MagicMock(), add_calls=[])
    mock_sm.return_value = _make_async_cm(session)

    with pytest.raises(UserNotFoundError, match="не найден"):
        await transfer_user_balance_to_cabinet(
            user_telegram_id=999999,
            cabinet_id=1,
            amount=100.0,
        )

    assert len(add_calls) == 0


@patch("app.modules.balance_manager.balance_service.sm")
async def test_transfer_user_balance_to_cabinet_cabinet_not_found(mock_sm):
    """Кабинет не найден -> CabinetNotFoundError."""
    user = _make_user_with_balance(1000.0)

    async def get(model, pk):
        if "WBCabinet" in str(type(model)):
            return None
        if "User" in str(type(model)):
            return user
        return None

    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session.execute = AsyncMock(return_value=result)
    session.get = get
    add_calls = []
    session.add = lambda obj: add_calls.append(obj)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    mock_sm.return_value = _make_async_cm(session)

    with pytest.raises(CabinetNotFoundError, match="Кабинет"):
        await transfer_user_balance_to_cabinet(
            user_telegram_id=12345,
            cabinet_id=999,
            amount=100.0,
        )

    assert len(add_calls) == 0


@pytest.mark.asyncio
async def test_transfer_user_balance_to_cabinet_zero_amount_raises():
    """Сумма 0 или отрицательная -> InvalidAmountError."""
    with pytest.raises(InvalidAmountError, match="положительной"):
        await transfer_user_balance_to_cabinet(
            user_telegram_id=12345,
            cabinet_id=1,
            amount=0.0,
        )
    with pytest.raises(InvalidAmountError, match="положительной"):
        await transfer_user_balance_to_cabinet(
            user_telegram_id=12345,
            cabinet_id=1,
            amount=-50.0,
        )
