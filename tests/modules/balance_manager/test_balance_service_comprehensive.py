"""Комплексные тесты для balance_service с полным покрытием всех сценариев."""

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.balance_manager.balance_service import process_payment_with_bonus
from app.modules.balance_manager.exceptions import (
    CabinetNotFoundError,
    InvalidAmountError,
    UserNotFoundError,
)


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_process_payment_with_bonus_fractional_percent():
    """Тест: проверка работы с дробными процентами."""
    user_id = 1
    cabinet_id = 1
    amount = 1000.0
    bonus_percent = 50.5  # Дробный процент

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

        expected_bonus = amount * (bonus_percent / 100)  # 505.0
        assert returned_bonus_amount == expected_bonus
        mock_add_bonus.assert_called_once_with(
            user_id, cabinet_id, expected_bonus, f"Бонус {bonus_percent}% при пополнении баланса"
        )


@pytest.mark.asyncio
async def test_process_payment_with_bonus_negative_amount_raises_error():
    """Тест: отрицательная сумма вызывает ошибку."""
    user_id = 1
    cabinet_id = 1
    amount = -100.0
    bonus_percent = 200.0

    with pytest.raises(InvalidAmountError, match="Сумма пополнения должна быть положительной"):
        await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
        )


@pytest.mark.asyncio
async def test_process_payment_with_bonus_description_passed_correctly():
    """Тест: проверка что description передается правильно."""
    user_id = 1
    cabinet_id = 1
    amount = 1000.0
    bonus_percent = 200.0
    description = "Кастомное описание"

    with patch(
        "app.modules.balance_manager.balance_service.add_balance"
    ) as mock_add_balance, patch(
        "app.modules.balance_manager.balance_service.add_bonus"
    ) as mock_add_bonus:
        mock_balance_payment = AsyncMock()
        mock_add_balance.return_value = mock_balance_payment

        mock_bonus_payment = AsyncMock()
        mock_add_bonus.return_value = mock_bonus_payment

        await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
            description=description,
        )

        # Проверяем, что description был передан в add_balance
        mock_add_balance.assert_called_once_with(user_id, cabinet_id, amount, description)


@pytest.mark.asyncio
async def test_process_payment_with_bonus_no_description_uses_default():
    """Тест: когда description не передан, используется значение по умолчанию."""
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

        await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
            description=None,
        )

        # Проверяем, что description=None был передан
        call_args = mock_add_balance.call_args
        # add_balance вызывается позиционными аргументами
        assert call_args.args[3] is None


@pytest.mark.asyncio
async def test_process_payment_with_bonus_add_balance_raises_user_not_found():
    """Тест: когда add_balance выбрасывает UserNotFoundError, оно пробрасывается."""
    user_id = 999
    cabinet_id = 1
    amount = 1000.0
    bonus_percent = 200.0

    with patch(
        "app.modules.balance_manager.balance_service.add_balance"
    ) as mock_add_balance:
        mock_add_balance.side_effect = UserNotFoundError(f"Пользователь с ID {user_id} не найден")

        with pytest.raises(UserNotFoundError):
            await process_payment_with_bonus(
                user_id=user_id,
                cabinet_id=cabinet_id,
                amount=amount,
                bonus_percent=bonus_percent,
            )


@pytest.mark.asyncio
async def test_process_payment_with_bonus_add_balance_raises_cabinet_not_found():
    """Тест: когда add_balance выбрасывает CabinetNotFoundError, оно пробрасывается."""
    user_id = 1
    cabinet_id = 999
    amount = 1000.0
    bonus_percent = 200.0

    with patch(
        "app.modules.balance_manager.balance_service.add_balance"
    ) as mock_add_balance:
        mock_add_balance.side_effect = CabinetNotFoundError(
            f"Кабинет с ID {cabinet_id} не найден"
        )

        with pytest.raises(CabinetNotFoundError):
            await process_payment_with_bonus(
                user_id=user_id,
                cabinet_id=cabinet_id,
                amount=amount,
                bonus_percent=bonus_percent,
            )


@pytest.mark.asyncio
async def test_process_payment_with_bonus_add_bonus_raises_error():
    """Тест: когда add_bonus выбрасывает ошибку, она пробрасывается."""
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

        mock_add_bonus.side_effect = CabinetNotFoundError(f"Кабинет с ID {cabinet_id} не найден")

        with pytest.raises(CabinetNotFoundError):
            await process_payment_with_bonus(
                user_id=user_id,
                cabinet_id=cabinet_id,
                amount=amount,
                bonus_percent=bonus_percent,
            )


@pytest.mark.asyncio
async def test_process_payment_with_bonus_zero_bonus_percent_no_add_bonus_call():
    """Тест: когда bonus_percent=0, add_bonus не вызывается."""
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

        await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
        )

        mock_add_balance.assert_called_once()
        mock_add_bonus.assert_not_called()


@pytest.mark.asyncio
async def test_process_payment_with_bonus_very_small_amount():
    """Тест: проверка работы с очень маленькими суммами."""
    user_id = 1
    cabinet_id = 1
    amount = 0.01  # Минимальная сумма
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

        _, _, returned_amount, returned_bonus_amount = await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
        )

        assert returned_amount == amount
        expected_bonus = amount * 2  # 0.02
        assert abs(returned_bonus_amount - expected_bonus) < 0.0001  # Учитываем погрешность float


@pytest.mark.asyncio
async def test_process_payment_with_bonus_very_large_amount():
    """Тест: проверка работы с очень большими суммами."""
    user_id = 1
    cabinet_id = 1
    amount = 1000000.0  # 1 миллион рублей
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

        _, _, returned_amount, returned_bonus_amount = await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
        )

        assert returned_amount == amount
        assert returned_bonus_amount == amount * 2


@pytest.mark.asyncio
async def test_process_payment_with_bonus_bonus_description_format():
    """Тест: проверка формата описания бонуса."""
    user_id = 1
    cabinet_id = 1
    amount = 1000.0
    bonus_percent = 150.0

    with patch(
        "app.modules.balance_manager.balance_service.add_balance"
    ) as mock_add_balance, patch(
        "app.modules.balance_manager.balance_service.add_bonus"
    ) as mock_add_bonus:
        mock_balance_payment = AsyncMock()
        mock_add_balance.return_value = mock_balance_payment

        mock_bonus_payment = AsyncMock()
        mock_add_bonus.return_value = mock_bonus_payment

        await process_payment_with_bonus(
            user_id=user_id,
            cabinet_id=cabinet_id,
            amount=amount,
            bonus_percent=bonus_percent,
        )

        # Проверяем формат описания бонуса
        call_args = mock_add_bonus.call_args
        # add_bonus вызывается позиционными аргументами
        bonus_description = call_args.args[3]
        assert bonus_description == f"Бонус {bonus_percent}% при пополнении баланса"


