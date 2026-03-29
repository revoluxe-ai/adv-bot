"""Тесты для проверки логики начисления бонуса с учетом даты в handlers."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.balance_manager.handlers import successful_payment_handler


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_bonus_awarded_before_end_of_2025():
    """Тест: до 31.12.2025 включительно бонус начисляется."""
    # Мокируем date.today() чтобы вернуть дату до конца 2025 года
    test_date = date(2025, 12, 31)  # Последний день года

    with patch("app.modules.balance_manager.handlers.date") as mock_date_module, patch(
        "app.modules.balance_manager.handlers.process_payment_with_bonus"
    ) as mock_process_payment, patch(
        "app.modules.balance_manager.handlers.sm"
    ) as mock_sm, patch(
        "app.modules.balance_manager.handlers.messages"
    ) as mock_messages, patch(
        "app.modules.balance_manager.handlers.ShopMenu"
    ) as mock_shop_menu, patch(
        "app.modules.balance_manager.handlers.asyncio.sleep"
    ):
        # Мокируем date.today() и конструктор date()
        mock_date_module.today.return_value = test_date
        mock_date_module.side_effect = lambda *args, **kw: date(*args, **kw)

        # Мокируем настройки
        with patch("app.modules.balance_manager.handlers.settings") as mock_settings:
            mock_settings.BALANCE_TOPUP_BONUS_PERCENT = 200.0
            mock_settings.presentation_only = False

            # Мокируем сообщение и состояние
            mock_message = MagicMock()
            mock_message.chat.id = 12345
            mock_message.successful_payment.total_amount = 100000  # 1000 рублей в копейках
            mock_message.answer = AsyncMock()

            mock_state = MagicMock()
            mock_state.get_data = AsyncMock(
                return_value={"wb_cabinet_original_id_for_add_balance": 1}
            )

            mock_bot = MagicMock()

            # Мокируем первую сессию БД (для получения user_id)
            mock_session1 = MagicMock()
            mock_user_result = MagicMock()
            mock_user_result.scalar_one_or_none.return_value = 1
            mock_session1.execute = AsyncMock(return_value=mock_user_result)

            # Мокируем вторую сессию БД (для получения wb_user_cabinet_id)
            mock_session2 = MagicMock()
            mock_wb_user_cabinet_result = MagicMock()
            mock_wb_user_cabinet_result.scalars.return_value.first.return_value = 1
            mock_session2.execute = AsyncMock(return_value=mock_wb_user_cabinet_result)

            # Настраиваем контекстный менеджер для двух вызовов sm()
            mock_sm.return_value.__aenter__ = AsyncMock(
                side_effect=[mock_session1, mock_session2]
            )
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

            # Мокируем process_payment_with_bonus
            mock_process_payment.return_value = (
                MagicMock(),  # balance_payment
                MagicMock(),  # bonus_payment
                1000.0,       # amount
                2000.0,       # bonus_amount
            )

            # Мокируем messages.BalanceUpdated
            mock_balance_updated = AsyncMock()
            mock_messages.BalanceUpdated.return_value = mock_balance_updated

            # Мокируем ShopMenu
            mock_shop_menu_instance = AsyncMock()
            mock_shop_menu.return_value = mock_shop_menu_instance

            mock_event_manager = AsyncMock()
            await successful_payment_handler(
                mock_message,
                mock_state,
                mock_bot,
                billing_event_manager=mock_event_manager,
            )

            # Проверяем, что process_payment_with_bonus был вызван с bonus_percent=200
            mock_process_payment.assert_called_once()
            call_args = mock_process_payment.call_args
            assert call_args.kwargs["bonus_percent"] == 200.0, (
                "Бонус должен начисляться до конца 2025 года"
            )


@pytest.mark.asyncio
async def test_bonus_not_awarded_after_end_of_2025():
    """Тест: после 31.12.2025 бонус не начисляется."""
    # Мокируем date.today() чтобы вернуть дату после конца 2025 года
    test_date = date(2026, 1, 1)  # Первый день 2026 года

    with patch("app.modules.balance_manager.handlers.date") as mock_date_module, patch(
        "app.modules.balance_manager.handlers.process_payment_with_bonus"
    ) as mock_process_payment, patch(
        "app.modules.balance_manager.handlers.sm"
    ) as mock_sm, patch(
        "app.modules.balance_manager.handlers.messages"
    ) as mock_messages, patch(
        "app.modules.balance_manager.handlers.ShopMenu"
    ) as mock_shop_menu, patch(
        "app.modules.balance_manager.handlers.asyncio.sleep"
    ):
        mock_date_module.today.return_value = test_date
        mock_date_module.side_effect = lambda *args, **kw: date(*args, **kw)

        # Мокируем настройки
        with patch("app.modules.balance_manager.handlers.settings") as mock_settings:
            mock_settings.BALANCE_TOPUP_BONUS_PERCENT = 200.0
            mock_settings.presentation_only = False

            # Мокируем сообщение и состояние
            mock_message = MagicMock()
            mock_message.chat.id = 12345
            mock_message.successful_payment.total_amount = 100000  # 1000 рублей в копейках
            mock_message.answer = AsyncMock()

            mock_state = MagicMock()
            mock_state.get_data = AsyncMock(
                return_value={"wb_cabinet_original_id_for_add_balance": 1}
            )

            mock_bot = MagicMock()

            # Мокируем первую сессию БД (для получения user_id)
            mock_session1 = MagicMock()
            mock_user_result = MagicMock()
            mock_user_result.scalar_one_or_none.return_value = 1
            mock_session1.execute = AsyncMock(return_value=mock_user_result)

            # Мокируем вторую сессию БД (для получения wb_user_cabinet_id)
            mock_session2 = MagicMock()
            mock_wb_user_cabinet_result = MagicMock()
            mock_wb_user_cabinet_result.scalars.return_value.first.return_value = 1
            mock_session2.execute = AsyncMock(return_value=mock_wb_user_cabinet_result)

            # Настраиваем контекстный менеджер для двух вызовов sm()
            mock_sm.return_value.__aenter__ = AsyncMock(
                side_effect=[mock_session1, mock_session2]
            )
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

            # Мокируем process_payment_with_bonus
            mock_process_payment.return_value = (
                MagicMock(),  # balance_payment
                None,         # bonus_payment (нет бонуса)
                1000.0,       # amount
                0.0,          # bonus_amount
            )

            # Мокируем messages.BalanceUpdated
            mock_balance_updated = AsyncMock()
            mock_messages.BalanceUpdated.return_value = mock_balance_updated

            # Мокируем ShopMenu
            mock_shop_menu_instance = AsyncMock()
            mock_shop_menu.return_value = mock_shop_menu_instance

            mock_event_manager = AsyncMock()
            await successful_payment_handler(
                mock_message,
                mock_state,
                mock_bot,
                billing_event_manager=mock_event_manager,
            )

            # Проверяем, что process_payment_with_bonus был вызван с bonus_percent=0
            mock_process_payment.assert_called_once()
            call_args = mock_process_payment.call_args
            assert call_args.kwargs["bonus_percent"] == 0.0, (
                "Бонус не должен начисляться после конца 2025 года"
            )


@pytest.mark.asyncio
async def test_bonus_awarded_on_last_day_of_2025():
    """Тест: на последний день 2025 года (31.12.2025) бонус начисляется."""
    test_date = date(2025, 12, 31)  # Последний день года

    with patch("app.modules.balance_manager.handlers.date") as mock_date_module, patch(
        "app.modules.balance_manager.handlers.process_payment_with_bonus"
    ) as mock_process_payment, patch(
        "app.modules.balance_manager.handlers.sm"
    ) as mock_sm, patch(
        "app.modules.balance_manager.handlers.messages"
    ) as mock_messages, patch(
        "app.modules.balance_manager.handlers.ShopMenu"
    ) as mock_shop_menu, patch(
        "app.modules.balance_manager.handlers.asyncio.sleep"
    ):
        mock_date_module.today.return_value = test_date
        mock_date_module.side_effect = lambda *args, **kw: date(*args, **kw)

        with patch("app.modules.balance_manager.handlers.settings") as mock_settings:
            mock_settings.BALANCE_TOPUP_BONUS_PERCENT = 200.0
            mock_settings.presentation_only = False

            mock_message = MagicMock()
            mock_message.chat.id = 12345
            mock_message.successful_payment.total_amount = 100000
            mock_message.answer = AsyncMock()

            mock_state = MagicMock()
            mock_state.get_data = AsyncMock(
                return_value={"wb_cabinet_original_id_for_add_balance": 1}
            )

            mock_bot = MagicMock()

            # Мокируем первую сессию БД (для получения user_id)
            mock_session1 = MagicMock()
            mock_user_result = MagicMock()
            mock_user_result.scalar_one_or_none.return_value = 1
            mock_session1.execute = AsyncMock(return_value=mock_user_result)

            # Мокируем вторую сессию БД (для получения wb_user_cabinet_id)
            mock_session2 = MagicMock()
            mock_wb_user_cabinet_result = MagicMock()
            mock_wb_user_cabinet_result.scalars.return_value.first.return_value = 1
            mock_session2.execute = AsyncMock(return_value=mock_wb_user_cabinet_result)

            # Настраиваем контекстный менеджер для двух вызовов sm()
            mock_sm.return_value.__aenter__ = AsyncMock(
                side_effect=[mock_session1, mock_session2]
            )
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_process_payment.return_value = (
                MagicMock(),
                MagicMock(),
                1000.0,
                2000.0,
            )

            # Мокируем messages.BalanceUpdated
            mock_balance_updated = AsyncMock()
            mock_messages.BalanceUpdated.return_value = mock_balance_updated

            mock_shop_menu_instance = AsyncMock()
            mock_shop_menu.return_value = mock_shop_menu_instance

            mock_event_manager = AsyncMock()
            await successful_payment_handler(
                mock_message,
                mock_state,
                mock_bot,
                billing_event_manager=mock_event_manager,
            )

            call_args = mock_process_payment.call_args
            assert call_args.kwargs["bonus_percent"] == 200.0, (
                "Бонус должен начисляться включительно до 31.12.2025"
            )

