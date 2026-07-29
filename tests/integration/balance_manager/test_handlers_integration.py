"""Интеграционные тесты для handlers с реальной БД и проверкой даты."""

import json
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.balance_manager.balance_service import get_cabinet_balance
from app.modules.balance_manager.handlers import successful_payment_handler
from app.modules.common_slaves.wildberries.models import WBBalancePayment, WBBonusPayment, WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User


pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


async def _create_test_user(
    session: AsyncSession,
    user_telegram_id: int = 12345,
    passed_gate: bool = True,
) -> User:
    """Создает тестового пользователя."""
    user = User(
        user_telegram_id=user_telegram_id,
        username="test_user",
        passed_gate=passed_gate,
    )
    session.add(user)
    await session.flush()
    # Сервисы balance_service используют собственные сессии, поэтому данные должны быть закоммичены.
    await session.commit()
    return user


async def _create_wb_user_cabinet(
    session: AsyncSession, user: User, cabinet: WBCabinet
) -> WBUserCabinet:
    """Создает связь между пользователем и кабинетом."""
    wb_user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=cabinet.id,
        name="Test Cabinet",
    )
    session.add(wb_user_cabinet)
    await session.flush()
    await session.commit()
    return wb_user_cabinet


@pytest.mark.asyncio
async def test_successful_payment_handler_integration_bonus_before_2026(
    async_session: AsyncSession,
    cabinet: WBCabinet,
):
    """Интеграционный тест: обработка платежа с бонусом до конца 2025 года."""
    user = await _create_test_user(async_session, user_telegram_id=99999)
    _ = await _create_wb_user_cabinet(async_session, user, cabinet)

    test_date = date(2025, 6, 15)

    with patch("app.modules.balance_manager.handlers.date") as mock_date_module, patch(
        "app.modules.balance_manager.handlers.messages"
    ) as mock_messages, patch(
        "app.modules.balance_manager.handlers.ShopMenu"
    ) as mock_shop_menu, patch(
        "app.modules.balance_manager.handlers.asyncio.sleep"
    ):
        mock_date_module.today.return_value = test_date
        mock_date_module.side_effect = lambda *args: date(*args)  # type: ignore[misc]

        with patch("app.modules.balance_manager.handlers.settings") as mock_settings:
            mock_settings.BALANCE_TOPUP_BONUS_PERCENT = 200.0
            mock_settings.presentation_only = False

            mock_message = MagicMock()
            mock_message.chat.id = user.user_telegram_id
            mock_message.successful_payment.total_amount = 100000  # 1000 рублей
            mock_message.answer = AsyncMock()

            mock_state = MagicMock()
            mock_state.get_data = AsyncMock(
                return_value={"wb_cabinet_original_id_for_add_balance": cabinet.id}
            )

            mock_bot = MagicMock()

            mock_balance_updated = AsyncMock()
            mock_messages.BalanceUpdated.return_value = mock_balance_updated

            mock_shop_menu_instance = AsyncMock()
            mock_shop_menu.return_value = mock_shop_menu_instance

            mock_event_manager = AsyncMock()
            await successful_payment_handler(
                mock_message, mock_state, mock_bot, billing_event_manager=mock_event_manager
            )

            # Проверяем, что платежи созданы в БД
            balance_payments_stmt = select(WBBalancePayment).where(
                WBBalancePayment.wb_cabinet_id == cabinet.id
            )
            balance_payments_result = await async_session.execute(balance_payments_stmt)
            balance_payments = balance_payments_result.scalars().all()
            assert len(balance_payments) == 1
            assert balance_payments[0].amount == 1000.0

            bonus_payments_stmt = select(WBBonusPayment).where(
                WBBonusPayment.wb_cabinet_id == cabinet.id
            )
            bonus_payments_result = await async_session.execute(bonus_payments_stmt)
            bonus_payments = bonus_payments_result.scalars().all()
            assert len(bonus_payments) == 1
            assert bonus_payments[0].amount == 2000.0  # 200% от 1000

            # Проверяем calculated_balance и calculated_bonus через сервис
            balance, bonus = await get_cabinet_balance(cabinet.id)
            assert balance == 1000.0
            assert bonus == 2000.0

            # Проверяем, что BalanceUpdated был вызван
            mock_messages.BalanceUpdated.assert_called_once()
            call_args = mock_messages.BalanceUpdated.call_args
            assert call_args[0][2] == 1000.0  # amount
            assert call_args[0][3] == 2000.0  # bonus_amount


@pytest.mark.asyncio
async def test_successful_payment_handler_integration_no_bonus_after_2025(
    async_session: AsyncSession,
    cabinet: WBCabinet,
):
    """Интеграционный тест: обработка платежа без бонуса после 2025 года."""
    user = await _create_test_user(async_session, user_telegram_id=88888)
    _ = await _create_wb_user_cabinet(async_session, user, cabinet)

    test_date = date(2026, 1, 1)

    with patch("app.modules.balance_manager.handlers.date") as mock_date_module, patch(
        "app.modules.balance_manager.handlers.messages"
    ) as mock_messages, patch(
        "app.modules.balance_manager.handlers.ShopMenu"
    ) as mock_shop_menu, patch(
        "app.modules.balance_manager.handlers.asyncio.sleep"
    ):
        mock_date_module.today.return_value = test_date
        mock_date_module.side_effect = lambda *args: date(*args)  # type: ignore[misc]

        with patch("app.modules.balance_manager.handlers.settings") as mock_settings:
            mock_settings.BALANCE_TOPUP_BONUS_PERCENT = 200.0

            mock_message = MagicMock()
            mock_message.chat.id = user.user_telegram_id
            mock_message.successful_payment.total_amount = 100000  # 1000 рублей
            mock_message.answer = AsyncMock()

            mock_state = MagicMock()
            mock_state.get_data = AsyncMock(
                return_value={"wb_cabinet_original_id_for_add_balance": cabinet.id}
            )

            mock_bot = MagicMock()

            mock_balance_updated = AsyncMock()
            mock_messages.BalanceUpdated.return_value = mock_balance_updated

            mock_shop_menu_instance = AsyncMock()
            mock_shop_menu.return_value = mock_shop_menu_instance

            mock_event_manager = AsyncMock()
            await successful_payment_handler(
                mock_message, mock_state, mock_bot, billing_event_manager=mock_event_manager
            )

            # Проверяем, что платеж создан, но бонуса нет
            balance_payments_stmt = select(WBBalancePayment).where(
                WBBalancePayment.wb_cabinet_id == cabinet.id
            )
            balance_payments_result = await async_session.execute(balance_payments_stmt)
            balance_payments = balance_payments_result.scalars().all()
            assert len(balance_payments) == 1
            assert balance_payments[0].amount == 1000.0

            bonus_payments_stmt = select(WBBonusPayment).where(
                WBBonusPayment.wb_cabinet_id == cabinet.id
            )
            bonus_payments_result = await async_session.execute(bonus_payments_stmt)
            bonus_payments = bonus_payments_result.scalars().all()
            assert len(bonus_payments) == 0  # Бонусов нет

            # Проверяем calculated_balance и calculated_bonus через сервис
            balance, bonus = await get_cabinet_balance(cabinet.id)
            assert balance == 1000.0
            assert bonus == 0.0

            # Проверяем, что BalanceUpdated был вызван с bonus_amount=0
            call_args = mock_messages.BalanceUpdated.call_args
            assert call_args[0][2] == 1000.0  # amount
            assert call_args[0][3] == 0.0  # bonus_amount


@pytest.mark.asyncio
async def test_successful_payment_handler_user_not_found_integration(
    async_session: AsyncSession,
    cabinet: WBCabinet,
):
    """Интеграционный тест: обработка случая когда пользователь не найден."""
    test_date = date(2025, 6, 15)

    with patch("app.modules.balance_manager.handlers.date") as mock_date_module:
        mock_date_module.today.return_value = test_date
        mock_date_module.side_effect = lambda *args: date(*args)  # type: ignore[misc]

        mock_message = MagicMock()
        mock_message.chat.id = 999999  # Несуществующий пользователь
        mock_message.successful_payment.total_amount = 100000
        mock_message.answer = AsyncMock()

        mock_state = MagicMock()
        mock_state.get_data = AsyncMock(
            return_value={"wb_cabinet_original_id_for_add_balance": cabinet.id}
        )

        mock_bot = MagicMock()

        mock_event_manager = AsyncMock()
        await successful_payment_handler(
            mock_message, mock_state, mock_bot, billing_event_manager=mock_event_manager
        )

        # Проверяем, что было отправлено сообщение об ошибке
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "ошибка" in call_args.lower() or "поддержку" in call_args.lower()

        # Проверяем, что платежи НЕ созданы
        balance_payments_stmt = select(WBBalancePayment).where(
            WBBalancePayment.wb_cabinet_id == cabinet.id
        )
        balance_payments_result = await async_session.execute(balance_payments_stmt)
        balance_payments = balance_payments_result.scalars().all()
        assert len(balance_payments) == 0


@pytest.mark.asyncio
async def test_successful_payment_gate_entry_does_not_open_gate(
    async_session: AsyncSession,
):
    """Входной платёж через gate_entry больше не открывает passed_gate."""
    from app.client_bot.const import GATE_ENTRY_AMOUNT

    user = await _create_test_user(
        async_session, user_telegram_id=77777, passed_gate=False
    )
    assert user.passed_gate is False

    test_date = date(2025, 6, 15)
    payload = {"target": "user", "gate_entry": True}

    with patch("app.modules.balance_manager.handlers.date") as mock_date_module, patch(
        "app.modules.balance_manager.handlers.messages"
    ) as mock_messages, patch(
        "app.modules.balance_manager.handlers.ShopChoice"
    ) as mock_shop_choice, patch(
        "app.modules.balance_manager.handlers.settings"
    ) as mock_settings:
        mock_date_module.today.return_value = test_date
        mock_date_module.side_effect = lambda *args: date(*args)  # type: ignore[misc]
        mock_settings.BALANCE_TOPUP_BONUS_PERCENT = 0.0

        mock_message = MagicMock()
        mock_message.chat.id = user.user_telegram_id
        mock_message.successful_payment = MagicMock()
        mock_message.successful_payment.total_amount = GATE_ENTRY_AMOUNT * 100
        mock_message.successful_payment.invoice_payload = json.dumps(payload)
        mock_message.answer = AsyncMock()

        mock_state = MagicMock()
        mock_state.get_data = AsyncMock(return_value={})

        mock_bot = MagicMock()

        async def _balance_updated_coro() -> None:
            pass

        mock_messages.BalanceUpdated.return_value = lambda: _balance_updated_coro()
        mock_shop_choice.return_value = AsyncMock()

        mock_event_manager = AsyncMock()
        await successful_payment_handler(
            mock_message,
            mock_state,
            mock_bot,
            billing_event_manager=mock_event_manager,
        )

    await async_session.refresh(user)
    assert user.passed_gate is False

