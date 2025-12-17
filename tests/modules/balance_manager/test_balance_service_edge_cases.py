"""Тесты для граничных случаев в balance_service."""

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.balance_manager.balance_service import process_payment_with_bonus
from app.modules.balance_manager.exceptions import InvalidAmountError


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_process_payment_with_bonus_bonus_percent_exactly_zero():
    """Тест: bonus_percent точно равен 0.0."""
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
        mock_add_balance.return_value = mock_balance_payment

        _, bonus_payment, _, returned_bonus_amount = await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
        )

        assert returned_bonus_amount == 0.0
        assert bonus_payment is None
        mock_add_bonus.assert_not_called()


@pytest.mark.asyncio
async def test_process_payment_with_bonus_bonus_percent_very_small_positive():
    """Тест: очень маленький положительный процент."""
    user_id = 1
    cabinet_id = 1
    amount = 1000.0
    bonus_percent = 0.01  # 0.01%

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

        expected_bonus = amount * (bonus_percent / 100)  # 0.1
        assert abs(returned_bonus_amount - expected_bonus) < 0.0001
        mock_add_bonus.assert_called_once()


@pytest.mark.asyncio
async def test_process_payment_with_bonus_bonus_percent_very_large():
    """Тест: очень большой процент."""
    user_id = 1
    cabinet_id = 1
    amount = 1000.0
    bonus_percent = 10000.0  # 10000%

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

        expected_bonus = amount * (bonus_percent / 100)  # 100000
        assert returned_bonus_amount == expected_bonus


@pytest.mark.asyncio
async def test_process_payment_with_bonus_return_values_structure():
    """Тест: проверка структуры возвращаемых значений."""
    user_id = 1
    cabinet_id = 1
    amount = 1000.0
    bonus_percent = 200.0

    with patch(
        "app.modules.balance_manager.balance_service.add_balance"
    ) as mock_add_balance, patch(
        "app.modules.balance_manager.balance_service.add_bonus"
    ) as mock_add_bonus:
        mock_balance_payment = AsyncMock()
        mock_add_balance.return_value = mock_balance_payment

        mock_bonus_payment = AsyncMock()
        mock_add_bonus.return_value = mock_bonus_payment

        result = await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
        )

        # Проверяем, что возвращается кортеж из 4 элементов
        assert isinstance(result, tuple)
        assert len(result) == 4

        balance_payment, bonus_payment, returned_amount, returned_bonus_amount = result

        assert balance_payment == mock_balance_payment
        assert bonus_payment == mock_bonus_payment
        assert returned_amount == amount
        assert returned_bonus_amount == amount * 2


@pytest.mark.asyncio
async def test_process_payment_with_bonus_bonus_amount_calculation_precision():
    """Тест: проверка точности расчета суммы бонуса."""
    user_id = 1
    cabinet_id = 1
    amount = 333.33
    bonus_percent = 200.0

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

        expected_bonus = amount * 2  # 666.66
        assert abs(returned_bonus_amount - expected_bonus) < 0.01  # Учитываем погрешность float

        # Проверяем, что add_bonus был вызван с правильной суммой
        call_args = mock_add_bonus.call_args
        bonus_amount_passed = call_args[0][2]  # Третий позиционный аргумент
        assert abs(bonus_amount_passed - expected_bonus) < 0.01


