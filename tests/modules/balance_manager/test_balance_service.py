"""Тесты для модуля balance_manager."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.balance_manager.balance_service import (
    process_payment_with_bonus,
)
from app.modules.balance_manager.exceptions import InvalidAmountError


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_process_payment_with_bonus_200_percent():
    """Тест: при пополнении на X начисляется бонус X*2 (200%)."""
    user_id = 1
    cabinet_id = 1
    amount = 1000.0
    bonus_percent = 200.0

    with patch(
        "app.modules.balance_manager.balance_service.add_balance"
    ) as mock_add_balance, patch(
        "app.modules.balance_manager.balance_service.add_bonus"
    ) as mock_add_bonus:
        # Мокируем возвращаемые значения
        mock_balance_payment = AsyncMock()
        mock_balance_payment.amount = amount
        mock_add_balance.return_value = mock_balance_payment

        mock_bonus_payment = AsyncMock()
        mock_bonus_payment.amount = amount * 2  # 2000
        mock_add_bonus.return_value = mock_bonus_payment

        (
            balance_payment,
            bonus_payment,
            returned_amount,
            returned_bonus_amount,
        ) = await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
            description="Тестовое пополнение",
        )

        # Проверяем, что функции были вызваны с правильными параметрами
        mock_add_balance.assert_called_once_with(
            user_id, cabinet_id, amount, "Тестовое пополнение"
        )
        mock_add_bonus.assert_called_once_with(
            user_id,
            cabinet_id,
            amount * 2,  # 2000
            "Бонус 200.0% при пополнении баланса",
        )

        # Проверяем возвращаемые значения
        assert returned_amount == amount
        assert returned_bonus_amount == amount * 2  # 2000
        assert bonus_payment is not None


@pytest.mark.asyncio
async def test_process_payment_with_bonus_zero_percent():
    """Тест: при bonus_percent=0 бонус не начисляется."""
    user_id = 1
    cabinet_id = 1
    amount = 1000.0
    bonus_percent = 0.0

    with patch(
        "app.modules.balance_manager.balance_service.add_balance"
    ) as mock_add_balance, patch(
        "app.modules.balance_manager.balance_service.add_bonus"
    ) as mock_add_bonus:
        mock_balance_payment = AsyncMock()
        mock_balance_payment.amount = amount
        mock_add_balance.return_value = mock_balance_payment

        (
            balance_payment,
            bonus_payment,
            returned_amount,
            returned_bonus_amount,
        ) = await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
        )

        mock_add_balance.assert_called_once()
        mock_add_bonus.assert_not_called()

        assert returned_amount == amount
        assert returned_bonus_amount == 0.0
        assert bonus_payment is None


@pytest.mark.asyncio
async def test_process_payment_with_bonus_negative_percent_raises_error():
    """Тест: отрицательный процент бонуса вызывает ошибку."""
    user_id = 1
    cabinet_id = 1
    amount = 1000.0
    bonus_percent = -10.0

    with pytest.raises(InvalidAmountError, match="Процент бонуса не может быть отрицательным"):
        await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
        )


@pytest.mark.asyncio
async def test_process_payment_with_bonus_zero_amount_raises_error():
    """Тест: нулевая или отрицательная сумма вызывает ошибку."""
    user_id = 1
    cabinet_id = 1
    amount = 0.0
    bonus_percent = 200.0

    with pytest.raises(InvalidAmountError, match="Сумма пополнения должна быть положительной"):
        await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
        )


@pytest.mark.asyncio
async def test_bonus_calculation_various_percents():
    """Тест: проверка расчета бонуса для разных процентов."""
    user_id = 1
    cabinet_id = 1
    amount = 1000.0

    test_cases = [
        (50.0, 500.0),   # 50% = 500
        (100.0, 1000.0), # 100% = 1000
        (200.0, 2000.0), # 200% = 2000
        (300.0, 3000.0), # 300% = 3000
    ]

    for bonus_percent, expected_bonus in test_cases:
        with patch(
            "app.modules.balance_manager.balance_service.add_balance"
        ) as mock_add_balance, patch(
            "app.modules.balance_manager.balance_service.add_bonus"
        ) as mock_add_bonus:
            mock_balance_payment = AsyncMock()
            mock_add_balance.return_value = mock_balance_payment

            mock_bonus_payment = AsyncMock()
            mock_add_bonus.return_value = mock_bonus_payment

            _, _, _, returned_bonus_amount = await process_payment_with_bonus(
                user_id=user_id,
                cabinet_id=cabinet_id,
                amount=amount,
                bonus_percent=bonus_percent,
            )

            assert returned_bonus_amount == expected_bonus, (
                f"Для {bonus_percent}% ожидался бонус {expected_bonus}, "
                f"получен {returned_bonus_amount}"
            )


