"""Комплексные тесты для handlers с полным покрытием всех сценариев."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.balance_manager.handlers import successful_payment_handler


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_successful_payment_user_not_found():
    """Тест: когда пользователь не найден, отправляется сообщение об ошибке."""
    test_date = date(2025, 6, 15)

    with patch("app.modules.balance_manager.handlers.date") as mock_date_module, patch(
        "app.modules.balance_manager.handlers.sm"
    ) as mock_sm:
        mock_date_module.today.return_value = test_date
        mock_date_module.side_effect = lambda *args, **kw: date(*args, **kw)

        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.successful_payment.total_amount = 100000
        mock_message.answer = AsyncMock()

        mock_state = MagicMock()
        mock_state.get_data = AsyncMock(
            return_value={"wb_cabinet_original_id_for_add_balance": 1}
        )

        mock_bot = MagicMock()

        # Мокируем сессию БД - пользователь не найден
        mock_session = MagicMock()
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = None  # Пользователь не найден
        mock_session.execute = AsyncMock(return_value=mock_user_result)
        mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

        await successful_payment_handler(mock_message, mock_state, mock_bot)

        # Проверяем, что было отправлено сообщение об ошибке
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "ошибка" in call_args.lower() or "поддержку" in call_args.lower()


@pytest.mark.asyncio
async def test_successful_payment_different_amounts():
    """Тест: проверка обработки различных сумм платежей."""
    test_date = date(2025, 6, 15)

    test_cases = [
        (10000, 100.0),   # 100 рублей
        (50000, 500.0),   # 500 рублей
        (100000, 1000.0), # 1000 рублей
        (500000, 5000.0), # 5000 рублей
    ]

    for total_amount_cents, expected_amount in test_cases:
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

                mock_message = MagicMock()
                mock_message.chat.id = 12345
                mock_message.successful_payment.total_amount = total_amount_cents
                mock_message.answer = AsyncMock()

                mock_state = MagicMock()
                mock_state.get_data = AsyncMock(
                    return_value={"wb_cabinet_original_id_for_add_balance": 1}
                )

                mock_bot = MagicMock()

                mock_session1 = MagicMock()
                mock_user_result = MagicMock()
                mock_user_result.scalar_one_or_none.return_value = 1
                mock_session1.execute = AsyncMock(return_value=mock_user_result)

                mock_session2 = MagicMock()
                mock_wb_user_cabinet_result = MagicMock()
                mock_wb_user_cabinet_result.scalars.return_value.first.return_value = 1
                mock_session2.execute = AsyncMock(return_value=mock_wb_user_cabinet_result)

                mock_sm.return_value.__aenter__ = AsyncMock(
                    side_effect=[mock_session1, mock_session2]
                )
                mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_process_payment.return_value = (
                    MagicMock(),
                    MagicMock(),
                    expected_amount,
                    expected_amount * 2,
                )

                mock_balance_updated = AsyncMock()
                mock_messages.BalanceUpdated.return_value = mock_balance_updated

                mock_shop_menu_instance = AsyncMock()
                mock_shop_menu.return_value = mock_shop_menu_instance

                await successful_payment_handler(mock_message, mock_state, mock_bot)

                # Проверяем, что process_payment_with_bonus был вызван с правильной суммой
                call_args = mock_process_payment.call_args
                assert call_args.kwargs["amount"] == expected_amount, (
                    f"Для {total_amount_cents} копеек ожидалась сумма {expected_amount}"
                )


@pytest.mark.asyncio
async def test_successful_payment_calls_balance_updated():
    """Тест: проверка что вызывается messages.BalanceUpdated с правильными параметрами."""
    test_date = date(2025, 6, 15)

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

            mock_message = MagicMock()
            mock_message.chat.id = 12345
            mock_message.successful_payment.total_amount = 100000
            mock_message.answer = AsyncMock()

            mock_state = MagicMock()
            mock_state.get_data = AsyncMock(
                return_value={"wb_cabinet_original_id_for_add_balance": 1}
            )

            mock_bot = MagicMock()

            mock_session1 = MagicMock()
            mock_user_result = MagicMock()
            mock_user_result.scalar_one_or_none.return_value = 1
            mock_session1.execute = AsyncMock(return_value=mock_user_result)

            mock_session2 = MagicMock()
            mock_wb_user_cabinet_result = MagicMock()
            mock_wb_user_cabinet_result.scalars.return_value.first.return_value = 1
            mock_session2.execute = AsyncMock(return_value=mock_wb_user_cabinet_result)

            mock_sm.return_value.__aenter__ = AsyncMock(
                side_effect=[mock_session1, mock_session2]
            )
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

            expected_amount = 1000.0
            expected_bonus = 2000.0
            mock_process_payment.return_value = (
                MagicMock(),
                MagicMock(),
                expected_amount,
                expected_bonus,
            )

            mock_balance_updated = AsyncMock()
            mock_messages.BalanceUpdated.return_value = mock_balance_updated

            mock_shop_menu_instance = AsyncMock()
            mock_shop_menu.return_value = mock_shop_menu_instance

            await successful_payment_handler(mock_message, mock_state, mock_bot)

            # Проверяем, что BalanceUpdated был вызван с правильными параметрами
            mock_messages.BalanceUpdated.assert_called_once_with(
                mock_bot, 12345, expected_amount, expected_bonus
            )
            mock_balance_updated.assert_called_once()


@pytest.mark.asyncio
async def test_successful_payment_calls_shop_menu():
    """Тест: проверка что вызывается ShopMenu с правильными параметрами."""
    test_date = date(2025, 6, 15)

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

            mock_message = MagicMock()
            mock_message.chat.id = 12345
            mock_message.successful_payment.total_amount = 100000
            mock_message.answer = AsyncMock()

            mock_state = MagicMock()
            mock_state.get_data = AsyncMock(
                return_value={"wb_cabinet_original_id_for_add_balance": 1}
            )

            mock_bot = MagicMock()

            mock_session1 = MagicMock()
            mock_user_result = MagicMock()
            mock_user_result.scalar_one_or_none.return_value = 1
            mock_session1.execute = AsyncMock(return_value=mock_user_result)

            expected_wb_user_cabinet_id = 42
            mock_session2 = MagicMock()
            mock_wb_user_cabinet_result = MagicMock()
            mock_wb_user_cabinet_result.scalars.return_value.first.return_value = (
                expected_wb_user_cabinet_id
            )
            mock_session2.execute = AsyncMock(return_value=mock_wb_user_cabinet_result)

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

            mock_balance_updated = AsyncMock()
            mock_messages.BalanceUpdated.return_value = mock_balance_updated

            mock_shop_menu_instance = AsyncMock()
            mock_shop_menu.return_value = mock_shop_menu_instance

            await successful_payment_handler(mock_message, mock_state, mock_bot)

            # Проверяем, что ShopMenu был вызван с правильными параметрами
            mock_shop_menu.assert_called_once_with(
                mock_bot, 12345, mock_state, expected_wb_user_cabinet_id
            )
            mock_shop_menu_instance.assert_called_once()


@pytest.mark.asyncio
async def test_bonus_date_boundary_cases():
    """Тест: граничные случаи с датами."""
    test_cases = [
        (date(2025, 1, 1), True, "Начало 2025 года - бонус должен начисляться"),
        (date(2025, 6, 15), True, "Середина 2025 года - бонус должен начисляться"),
        (date(2025, 12, 30), True, "Предпоследний день 2025 года - бонус должен начисляться"),
        (date(2025, 12, 31), True, "Последний день 2025 года - бонус должен начисляться"),
        (date(2026, 1, 1), False, "Первый день 2026 года - бонус НЕ должен начисляться"),
        (date(2026, 6, 15), False, "Середина 2026 года - бонус НЕ должен начисляться"),
    ]

    for test_date, should_have_bonus, description in test_cases:
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

                mock_message = MagicMock()
                mock_message.chat.id = 12345
                mock_message.successful_payment.total_amount = 100000
                mock_message.answer = AsyncMock()

                mock_state = MagicMock()
                mock_state.get_data = AsyncMock(
                    return_value={"wb_cabinet_original_id_for_add_balance": 1}
                )

                mock_bot = MagicMock()

                mock_session1 = MagicMock()
                mock_user_result = MagicMock()
                mock_user_result.scalar_one_or_none.return_value = 1
                mock_session1.execute = AsyncMock(return_value=mock_user_result)

                mock_session2 = MagicMock()
                mock_wb_user_cabinet_result = MagicMock()
                mock_wb_user_cabinet_result.scalars.return_value.first.return_value = 1
                mock_session2.execute = AsyncMock(return_value=mock_wb_user_cabinet_result)

                mock_sm.return_value.__aenter__ = AsyncMock(
                    side_effect=[mock_session1, mock_session2]
                )
                mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_process_payment.return_value = (
                    MagicMock(),
                    MagicMock() if should_have_bonus else None,
                    1000.0,
                    2000.0 if should_have_bonus else 0.0,
                )

                mock_balance_updated = AsyncMock()
                mock_messages.BalanceUpdated.return_value = mock_balance_updated

                mock_shop_menu_instance = AsyncMock()
                mock_shop_menu.return_value = mock_shop_menu_instance

                await successful_payment_handler(mock_message, mock_state, mock_bot)

                call_args = mock_process_payment.call_args
                expected_bonus_percent = 200.0 if should_have_bonus else 0.0
                assert call_args.kwargs["bonus_percent"] == expected_bonus_percent, (
                    f"{description}: ожидался bonus_percent={expected_bonus_percent}, "
                    f"получен {call_args.kwargs['bonus_percent']}"
                )


@pytest.mark.asyncio
async def test_successful_payment_description():
    """Тест: проверка что description передается правильно."""
    test_date = date(2025, 6, 15)

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

            mock_message = MagicMock()
            mock_message.chat.id = 12345
            mock_message.successful_payment.total_amount = 100000
            mock_message.answer = AsyncMock()

            mock_state = MagicMock()
            mock_state.get_data = AsyncMock(
                return_value={"wb_cabinet_original_id_for_add_balance": 1}
            )

            mock_bot = MagicMock()

            mock_session1 = MagicMock()
            mock_user_result = MagicMock()
            mock_user_result.scalar_one_or_none.return_value = 1
            mock_session1.execute = AsyncMock(return_value=mock_user_result)

            mock_session2 = MagicMock()
            mock_wb_user_cabinet_result = MagicMock()
            mock_wb_user_cabinet_result.scalars.return_value.first.return_value = 1
            mock_session2.execute = AsyncMock(return_value=mock_wb_user_cabinet_result)

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

            mock_balance_updated = AsyncMock()
            mock_messages.BalanceUpdated.return_value = mock_balance_updated

            mock_shop_menu_instance = AsyncMock()
            mock_shop_menu.return_value = mock_shop_menu_instance

            await successful_payment_handler(mock_message, mock_state, mock_bot)

            # Проверяем, что description был передан правильно
            call_args = mock_process_payment.call_args
            assert call_args.kwargs["description"] == "Пополнение баланса через Telegram"


