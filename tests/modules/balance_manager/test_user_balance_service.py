"""Тесты для user_balance_service (личный баланс по user_telegram_id)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.balance_manager.exceptions import InvalidAmountError, UserNotFoundError
from app.modules.balance_manager.user_balance_service import (
    add_user_balance,
    add_user_bonus,
    get_user_balance,
    process_user_payment_with_bonus,
)

pytestmark = pytest.mark.asyncio


async def test_add_user_balance_zero_raises() -> None:
    """add_user_balance при amount <= 0 raises InvalidAmountError."""
    with pytest.raises(InvalidAmountError, match="положительной"):
        await add_user_balance(user_telegram_id=1, amount=0.0)
    with pytest.raises(InvalidAmountError, match="положительной"):
        await add_user_balance(user_telegram_id=1, amount=-100.0)


async def test_add_user_bonus_zero_raises() -> None:
    """add_user_bonus при amount <= 0 raises InvalidAmountError."""
    with pytest.raises(InvalidAmountError, match="положительной"):
        await add_user_bonus(user_telegram_id=1, amount=0.0)


async def test_get_user_balance_user_not_found() -> None:
    """get_user_balance при отсутствии пользователя raises UserNotFoundError."""
    with patch("app.modules.balance_manager.user_balance_service.sm") as mock_sm:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(UserNotFoundError, match="не найден"):
            await get_user_balance(user_telegram_id=999999)


async def test_process_user_payment_with_bonus_negative_amount_raises() -> None:
    """process_user_payment_with_bonus при amount <= 0 raises InvalidAmountError."""
    with pytest.raises(InvalidAmountError):
        await process_user_payment_with_bonus(
            user_telegram_id=1,
            amount=0.0,
            bonus_percent=10.0,
        )


async def test_process_user_payment_with_bonus_negative_percent_raises() -> None:
    """process_user_payment_with_bonus при bonus_percent < 0 raises InvalidAmountError."""
    with pytest.raises(InvalidAmountError, match="Процент бонуса"):
        await process_user_payment_with_bonus(
            user_telegram_id=1,
            amount=100.0,
            bonus_percent=-5.0,
        )


@patch("app.modules.balance_manager.user_balance_service.add_user_bonus")
@patch("app.modules.balance_manager.user_balance_service.add_user_balance")
async def test_process_user_payment_with_bonus_calls(
    mock_add_balance: AsyncMock,
    mock_add_bonus: AsyncMock,
) -> None:
    """process_user_payment_with_bonus вызывает add_user_balance и при bonus > 0 add_user_bonus."""
    mock_balance_payment = MagicMock()
    mock_add_balance.return_value = mock_balance_payment
    mock_bonus_payment = MagicMock()
    mock_add_bonus.return_value = mock_bonus_payment

    (
        _,
        _,
        amount,
        bonus_amount,
    ) = await process_user_payment_with_bonus(
        user_telegram_id=100,
        amount=1000.0,
        bonus_percent=50.0,
        description="Pay",
    )

    mock_add_balance.assert_awaited_once_with(
        100,
        1000.0,
        "Pay",
    )
    mock_add_bonus.assert_awaited_once()
    call_args = mock_add_bonus.await_args[0]
    assert call_args[0] == 100
    assert call_args[1] == 500.0
    assert "50" in call_args[2]
    assert amount == 1000.0
    assert bonus_amount == 500.0


@patch("app.modules.balance_manager.user_balance_service.add_user_bonus")
@patch("app.modules.balance_manager.user_balance_service.add_user_balance")
async def test_process_user_payment_with_bonus_zero_percent_no_bonus(
    mock_add_balance: AsyncMock,
    mock_add_bonus: AsyncMock,
) -> None:
    """При bonus_percent=0 add_user_bonus не вызывается."""
    mock_add_balance.return_value = MagicMock()

    await process_user_payment_with_bonus(
        user_telegram_id=1,
        amount=100.0,
        bonus_percent=0.0,
    )

    mock_add_balance.assert_awaited_once()
    mock_add_bonus.assert_not_awaited()
