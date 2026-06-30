"""
Comprehensive tests for the add_new_token handler in start.py
Tests cover all workflow scenarios and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch
from aiogram.types import Message, User as TelegramUser
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import IntegrityError

from app.client_bot.user_interface.handlers.start.start import (
    DUPLICATE_TOKEN_MESSAGE,
    process_add_new_token,
)
from app.modules.common_slaves.wildberries.models import (
    WBToken,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet


@pytest.fixture
def mock_message():
    """Create a mock Telegram message"""
    message = MagicMock(spec=Message)
    message.text = "valid_token_string"
    chat_mock = MagicMock()
    chat_mock.id = 12345
    message.chat = chat_mock

    # Mock from_user
    user = MagicMock(spec=TelegramUser)
    user.id = 67890
    message.from_user = user

    return message


@pytest.fixture
def mock_bot():
    """Create a mock Bot instance"""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_state():
    """Create a mock FSMContext"""
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_client_session():
    """Create a mock aiohttp ClientSession for TokenPermissionsValidator."""
    return MagicMock()


@pytest.fixture
def mock_wb_user_cabinet():
    """Create a mock WBUserCabinet with a nested WBCabinet"""
    mock_cabinet = MagicMock(spec=WBCabinet)
    mock_cabinet.shop_id = "test_shop_id"
    mock_wb_user_cabinet_instance = MagicMock(spec=WBUserCabinet)
    mock_wb_user_cabinet_instance.id = 1
    mock_wb_user_cabinet_instance.name = "Test Cabinet"
    mock_wb_user_cabinet_instance.wb_cabinet_id = 1
    mock_wb_user_cabinet_instance.user_id = 12345
    mock_wb_user_cabinet_instance.wb_cabinet = mock_cabinet
    return mock_wb_user_cabinet_instance


def _build_validation_result(shop_id: str) -> MagicMock:
    """Return a successful token validation result for a specific shop."""
    result = MagicMock()
    result.is_valid_jwt = True
    result.is_personal = True
    result.is_read_only = False
    result.is_expired = False
    result.can_be_used = True
    result.shop_id = shop_id
    result.missing_required = set()
    return result


def _build_token_process_message(user_id: int, chat_id: int, token: str) -> MagicMock:
    """Create a message mock for process_add_new_token tests."""
    message = MagicMock(spec=Message)
    message.text = token
    message.from_user = MagicMock(spec=TelegramUser)
    message.from_user.id = user_id
    message.chat = MagicMock()
    message.chat.id = chat_id
    return message


def _build_integrity_error() -> IntegrityError:
    """Create a synthetic IntegrityError for duplicate-token fallback tests."""
    return IntegrityError("insert into wb_token", params=None, orig=Exception("duplicate"))


class TestProcessAddNewToken:
    """Test suite for process_add_new_token handler"""

    @pytest.mark.asyncio
    async def test_empty_message_text(self, mock_message, mock_bot, mock_state, mock_client_session):
        """Test handler with empty message text - should return early"""
        mock_message.text = None

        result = await process_add_new_token(
            mock_message, mock_bot, mock_state, mock_client_session
        )

        assert result is None
        mock_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_command_triggers_restart(
        self, mock_message, mock_bot, mock_state, mock_client_session
    ):
        """Test /start command in message triggers registration restart"""
        mock_message.text = "/start"

        with patch(
            "app.client_bot.user_interface.handlers.start.start.start_registration"
        ) as mock_start_reg:
            mock_start_reg.return_value = AsyncMock()

            await process_add_new_token(
                mock_message, mock_bot, mock_state, mock_client_session
            )

            mock_start_reg.assert_called_once_with(mock_message, mock_bot, mock_state)

    @pytest.mark.asyncio
    async def test_duplicate_token_same_user(
        self, mock_bot, mock_state, mock_client_session, mock_wb_user_cabinet
    ):
        """Duplicate token owned by the current user reopens the shop menu."""
        good_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzc2OTk4Mjg4LCJpZCI6IjAxOWExMTgxLTc3ZjctNzA0Ni05ZmVkLTBkYWZiMTEzYjA5NSIsImlpZCI6NTQyNTkzMjQsIm9pZCI6NDA3OTM0OSwicyI6NzAsInNpZCI6IjI0YTk4OWVlLTM5Y2ItNDZjOC1hYzNmLWE4MzM3MGQ5NTg1ZiIsInQiOmZhbHNlLCJ1aWQiOjU0MjU5MzI0fQ.jFYQHctVOvRKSVz67O0WiLO7TrF-Z1YfYGcxbBmll8VQAEBjP-LsmigOk74HQfuvWSdDCNqcaQ0DizT-vXSkHA"
        shop_id = WBToken(api_key=good_token).get_shop_id_from_token()
        mock_wb_user_cabinet.wb_cabinet.shop_id = shop_id
        mock_message = _build_token_process_message(1, 111111, good_token)
        mock_existing_token = MagicMock(spec=WBToken)
        mock_existing_token.user_id = 1

        with patch(
            "app.client_bot.user_interface.handlers.start.start.TokenPermissionsValidator"
        ) as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate = AsyncMock(
                return_value=_build_validation_result(shop_id)
            )
            mock_validator_class.return_value = mock_validator

            with (
                patch("app.client_bot.user_interface.handlers.start.start.sm") as mock_sm,
                patch(
                    "app.client_bot.user_interface.handlers.start.start.is_bot_admin",
                    return_value=False,
                ),
                patch(
                    "app.client_bot.user_interface.handlers.start.start.ShopMenu"
                ) as mock_shop_menu_ctor,
            ):
                mock_session = MagicMock()
                mock_shop_menu = AsyncMock()
                mock_shop_menu_ctor.return_value = mock_shop_menu

                # First query - user found
                mock_user_result = MagicMock()
                mock_user_result.scalar.return_value = 1

                # Second query - cabinet found
                mock_cabinet_result = MagicMock()
                mock_cabinet_result.scalar.return_value = mock_wb_user_cabinet

                # Third query - existing token found for same user
                mock_token_result = MagicMock()
                mock_token_result.scalar.return_value = mock_existing_token

                mock_session.execute = AsyncMock(
                    side_effect=[
                        mock_user_result,
                        mock_cabinet_result,
                        mock_token_result,
                    ]
                )

                mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_sm.return_value.__aexit__ = AsyncMock()

                await process_add_new_token(
                    mock_message, mock_bot, mock_state, mock_client_session
                )

                assert mock_bot.send_message.call_count == 1
                call_args = mock_bot.send_message.call_args
                assert call_args == call(111111, DUPLICATE_TOKEN_MESSAGE)
                assert good_token not in call_args.args[1]
                mock_state.clear.assert_awaited_once()
                mock_shop_menu_ctor.assert_called_once_with(
                    mock_bot, 111111, mock_state, 1
                )
                mock_shop_menu.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_duplicate_token_visible_for_admin(
        self, mock_bot, mock_state, mock_client_session, mock_wb_user_cabinet
    ):
        """Duplicate token for another owner is visible only for admins."""
        good_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzc2OTk4Mjg4LCJpZCI6IjAxOWExMTgxLTc3ZjctNzA0Ni05ZmVkLTBkYWZiMTEzYjA5NSIsImlpZCI6NTQyNTkzMjQsIm9pZCI6NDA3OTM0OSwicyI6NzAsInNpZCI6IjI0YTk4OWVlLTM5Y2ItNDZjOC1hYzNmLWE4MzM3MGQ5NTg1ZiIsInQiOmZhbHNlLCJ1aWQiOjU0MjU5MzI0fQ.jFYQHctVOvRKSVz67O0WiLO7TrF-Z1YfYGcxbBmll8VQAEBjP-LsmigOk74HQfuvWSdDCNqcaQ0DizT-vXSkHA"
        shop_id = WBToken(api_key=good_token).get_shop_id_from_token()
        mock_wb_user_cabinet.wb_cabinet.shop_id = shop_id
        mock_message = _build_token_process_message(1, 111111, good_token)
        mock_existing_token = MagicMock(spec=WBToken)
        mock_existing_token.user_id = 999

        with (
            patch(
                "app.client_bot.user_interface.handlers.start.start.TokenPermissionsValidator"
            ) as mock_validator_class,
            patch("app.client_bot.user_interface.handlers.start.start.sm") as mock_sm,
            patch(
                "app.client_bot.user_interface.handlers.start.start.is_bot_admin",
                return_value=True,
            ),
            patch("app.client_bot.user_interface.handlers.start.start.ShopMenu") as mock_shop_menu_ctor,
        ):
            mock_validator = MagicMock()
            mock_validator.validate = AsyncMock(
                return_value=_build_validation_result(shop_id)
            )
            mock_validator_class.return_value = mock_validator

            mock_session = MagicMock()
            mock_shop_menu = AsyncMock()
            mock_shop_menu_ctor.return_value = mock_shop_menu

            mock_user_result = MagicMock()
            mock_user_result.scalar.return_value = 1

            mock_cabinet_result = MagicMock()
            mock_cabinet_result.scalar.return_value = mock_wb_user_cabinet

            mock_token_result = MagicMock()
            mock_token_result.scalar.return_value = mock_existing_token

            mock_session.execute = AsyncMock(
                side_effect=[mock_user_result, mock_cabinet_result, mock_token_result]
            )
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock()

            await process_add_new_token(
                mock_message, mock_bot, mock_state, mock_client_session
            )

            mock_bot.send_message.assert_awaited_once_with(
                111111, DUPLICATE_TOKEN_MESSAGE
            )
            mock_state.clear.assert_awaited_once()
            mock_shop_menu_ctor.assert_called_once_with(
                mock_bot, 111111, mock_state, 1
            )
            mock_shop_menu.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_duplicate_token_other_user_not_admin_hides_shop(
        self, mock_bot, mock_state, mock_client_session, mock_wb_user_cabinet
    ):
        """Foreign duplicate token must not reveal any shop details."""
        good_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzc2OTk4Mjg4LCJpZCI6IjAxOWExMTgxLTc3ZjctNzA0Ni05ZmVkLTBkYWZiMTEzYjA5NSIsImlpZCI6NTQyNTkzMjQsIm9pZCI6NDA3OTM0OSwicyI6NzAsInNpZCI6IjI0YTk4OWVlLTM5Y2ItNDZjOC1hYzNmLWE4MzM3MGQ5NTg1ZiIsInQiOmZhbHNlLCJ1aWQiOjU0MjU5MzI0fQ.jFYQHctVOvRKSVz67O0WiLO7TrF-Z1YfYGcxbBmll8VQAEBjP-LsmigOk74HQfuvWSdDCNqcaQ0DizT-vXSkHA"
        shop_id = WBToken(api_key=good_token).get_shop_id_from_token()
        mock_wb_user_cabinet.wb_cabinet.shop_id = shop_id
        mock_message = _build_token_process_message(1, 111111, good_token)
        mock_existing_token = MagicMock(spec=WBToken)
        mock_existing_token.user_id = 999

        with (
            patch(
                "app.client_bot.user_interface.handlers.start.start.TokenPermissionsValidator"
            ) as mock_validator_class,
            patch("app.client_bot.user_interface.handlers.start.start.sm") as mock_sm,
            patch(
                "app.client_bot.user_interface.handlers.start.start.is_bot_admin",
                return_value=False,
            ),
            patch("app.client_bot.user_interface.handlers.start.start.ShopMenu") as mock_shop_menu_ctor,
        ):
            mock_validator = MagicMock()
            mock_validator.validate = AsyncMock(
                return_value=_build_validation_result(shop_id)
            )
            mock_validator_class.return_value = mock_validator

            mock_session = MagicMock()
            mock_user_result = MagicMock()
            mock_user_result.scalar.return_value = 1
            mock_cabinet_result = MagicMock()
            mock_cabinet_result.scalar.return_value = mock_wb_user_cabinet
            mock_token_result = MagicMock()
            mock_token_result.scalar.return_value = mock_existing_token
            mock_session.execute = AsyncMock(
                side_effect=[mock_user_result, mock_cabinet_result, mock_token_result]
            )
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock()

            await process_add_new_token(
                mock_message, mock_bot, mock_state, mock_client_session
            )

            mock_bot.send_message.assert_awaited_once_with(
                111111, DUPLICATE_TOKEN_MESSAGE
            )
            mock_state.clear.assert_not_called()
            mock_shop_menu_ctor.assert_not_called()
            assert "Test Cabinet" not in mock_bot.send_message.call_args.args[1]
            assert good_token not in mock_bot.send_message.call_args.args[1]

    @pytest.mark.asyncio
    async def test_normal_new_token_flow_still_shows_success_shop(
        self, mock_bot, mock_state, mock_client_session, mock_wb_user_cabinet
    ):
        """New token flow keeps the old success path intact."""
        good_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzc2OTk4Mjg4LCJpZCI6IjAxOWExMTgxLTc3ZjctNzA0Ni05ZmVkLTBkYWZiMTEzYjA5NSIsImlpZCI6NTQyNTkzMjQsIm9pZCI6NDA3OTM0OSwicyI6NzAsInNpZCI6IjI0YTk4OWVlLTM5Y2ItNDZjOC1hYzNmLWE4MzM3MGQ5NTg1ZiIsInQiOmZhbHNlLCJ1aWQiOjU0MjU5MzI0fQ.jFYQHctVOvRKSVz67O0WiLO7TrF-Z1YfYGcxbBmll8VQAEBjP-LsmigOk74HQfuvWSdDCNqcaQ0DizT-vXSkHA"
        shop_id = WBToken(api_key=good_token).get_shop_id_from_token()
        mock_wb_user_cabinet.wb_cabinet.shop_id = shop_id
        mock_message = _build_token_process_message(1, 111111, good_token)

        with (
            patch(
                "app.client_bot.user_interface.handlers.start.start.TokenPermissionsValidator"
            ) as mock_validator_class,
            patch("app.client_bot.user_interface.handlers.start.start.sm") as mock_sm,
            patch(
                "app.client_bot.user_interface.handlers.start.start.NotificationManager"
            ) as mock_notification_manager_class,
            patch("app.client_bot.user_interface.handlers.start.start.ShopMenu") as mock_shop_menu_ctor,
        ):
            mock_validator = MagicMock()
            mock_validator.validate = AsyncMock(
                return_value=_build_validation_result(shop_id)
            )
            mock_validator_class.return_value = mock_validator

            mock_session = MagicMock()
            mock_shop_menu = AsyncMock()
            mock_shop_menu_ctor.return_value = mock_shop_menu

            mock_user_result = MagicMock()
            mock_user_result.scalar.return_value = 1
            mock_cabinet_result = MagicMock()
            mock_cabinet_result.scalar.return_value = mock_wb_user_cabinet
            mock_no_token_result = MagicMock()
            mock_no_token_result.scalar.return_value = None
            mock_activate_cabinet = MagicMock(spec=WBCabinet)
            mock_activate_cabinet.active = True
            mock_activate_result = MagicMock()
            mock_activate_result.scalar.return_value = mock_activate_cabinet

            mock_session.execute = AsyncMock(
                side_effect=[
                    mock_user_result,
                    mock_cabinet_result,
                    mock_no_token_result,
                    mock_activate_result,
                ]
            )
            mock_session.commit = AsyncMock()
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock()

            mock_notification_manager = MagicMock()
            mock_notification_manager.mark_notifications_resolved = AsyncMock(
                return_value=0
            )
            mock_notification_manager_class.return_value = mock_notification_manager

            await process_add_new_token(
                mock_message, mock_bot, mock_state, mock_client_session
            )

            assert mock_bot.send_message.await_args_list == [
                call(111111, "Токен проверяется..."),
                call(111111, "Токен успешно добавлен для магазина Test Cabinet!"),
            ]
            mock_state.clear.assert_awaited_once()
            mock_shop_menu_ctor.assert_called_once_with(
                mock_bot, 111111, mock_state, 1
            )
            mock_shop_menu.assert_awaited_once()
            sent_text = " ".join(args.args[1] for args in mock_bot.send_message.await_args_list)
            assert DUPLICATE_TOKEN_MESSAGE not in sent_text
            assert good_token not in sent_text

    @pytest.mark.asyncio
    async def test_duplicate_token_integrity_error_same_user_shows_shop(
        self, mock_bot, mock_state, mock_client_session, mock_wb_user_cabinet
    ):
        """IntegrityError fallback for the owner reuses duplicate helper and reopens ShopMenu."""
        good_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzc2OTk4Mjg4LCJpZCI6IjAxOWExMTgxLTc3ZjctNzA0Ni05ZmVkLTBkYWZiMTEzYjA5NSIsImlpZCI6NTQyNTkzMjQsIm9pZCI6NDA3OTM0OSwicyI6NzAsInNpZCI6IjI0YTk4OWVlLTM5Y2ItNDZjOC1hYzNmLWE4MzM3MGQ5NTg1ZiIsInQiOmZhbHNlLCJ1aWQiOjU0MjU5MzI0fQ.jFYQHctVOvRKSVz67O0WiLO7TrF-Z1YfYGcxbBmll8VQAEBjP-LsmigOk74HQfuvWSdDCNqcaQ0DizT-vXSkHA"
        shop_id = WBToken(api_key=good_token).get_shop_id_from_token()
        mock_wb_user_cabinet.wb_cabinet.shop_id = shop_id
        mock_message = _build_token_process_message(1, 111111, good_token)
        mock_existing_token = MagicMock(spec=WBToken)
        mock_existing_token.user_id = 1

        with (
            patch(
                "app.client_bot.user_interface.handlers.start.start.TokenPermissionsValidator"
            ) as mock_validator_class,
            patch("app.client_bot.user_interface.handlers.start.start.sm") as mock_sm,
            patch(
                "app.client_bot.user_interface.handlers.start.start.is_bot_admin",
                return_value=False,
            ),
            patch(
                "app.client_bot.user_interface.handlers.start.start._handle_duplicate_token_for_existing_shop",
                new_callable=AsyncMock,
            ) as mock_duplicate_helper,
        ):
            mock_validator = MagicMock()
            mock_validator.validate = AsyncMock(
                return_value=_build_validation_result(shop_id)
            )
            mock_validator_class.return_value = mock_validator

            mock_session = MagicMock()
            mock_user_result = MagicMock()
            mock_user_result.scalar.return_value = 1
            mock_cabinet_result = MagicMock()
            mock_cabinet_result.scalar.return_value = mock_wb_user_cabinet
            mock_no_token_result = MagicMock()
            mock_no_token_result.scalar.return_value = None
            mock_existing_token_result = MagicMock()
            mock_existing_token_result.scalar.return_value = mock_existing_token
            mock_session.execute = AsyncMock(
                side_effect=[
                    mock_user_result,
                    mock_cabinet_result,
                    mock_no_token_result,
                    mock_existing_token_result,
                ]
            )
            mock_session.commit = AsyncMock(side_effect=_build_integrity_error())
            mock_session.rollback = AsyncMock()
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock()

            await process_add_new_token(
                mock_message, mock_bot, mock_state, mock_client_session
            )

            mock_session.rollback.assert_awaited_once()
            mock_duplicate_helper.assert_awaited_once_with(
                bot=mock_bot,
                state=mock_state,
                chat_id=111111,
                current_user_id=1,
                current_user_telegram_id=1,
                existing_token=mock_existing_token,
                wb_user_cabinet_original_id=1,
            )

    @pytest.mark.asyncio
    async def test_duplicate_token_integrity_error_admin_shows_shop(
        self, mock_bot, mock_state, mock_client_session, mock_wb_user_cabinet
    ):
        """IntegrityError fallback for admins reuses duplicate helper and keeps shop visible."""
        good_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzc2OTk4Mjg4LCJpZCI6IjAxOWExMTgxLTc3ZjctNzA0Ni05ZmVkLTBkYWZiMTEzYjA5NSIsImlpZCI6NTQyNTkzMjQsIm9pZCI6NDA3OTM0OSwicyI6NzAsInNpZCI6IjI0YTk4OWVlLTM5Y2ItNDZjOC1hYzNmLWE4MzM3MGQ5NTg1ZiIsInQiOmZhbHNlLCJ1aWQiOjU0MjU5MzI0fQ.jFYQHctVOvRKSVz67O0WiLO7TrF-Z1YfYGcxbBmll8VQAEBjP-LsmigOk74HQfuvWSdDCNqcaQ0DizT-vXSkHA"
        shop_id = WBToken(api_key=good_token).get_shop_id_from_token()
        mock_wb_user_cabinet.wb_cabinet.shop_id = shop_id
        mock_message = _build_token_process_message(1, 111111, good_token)
        mock_existing_token = MagicMock(spec=WBToken)
        mock_existing_token.user_id = 999

        with (
            patch(
                "app.client_bot.user_interface.handlers.start.start.TokenPermissionsValidator"
            ) as mock_validator_class,
            patch("app.client_bot.user_interface.handlers.start.start.sm") as mock_sm,
            patch(
                "app.client_bot.user_interface.handlers.start.start.is_bot_admin",
                return_value=True,
            ),
            patch(
                "app.client_bot.user_interface.handlers.start.start._handle_duplicate_token_for_existing_shop",
                new_callable=AsyncMock,
            ) as mock_duplicate_helper,
        ):
            mock_validator = MagicMock()
            mock_validator.validate = AsyncMock(
                return_value=_build_validation_result(shop_id)
            )
            mock_validator_class.return_value = mock_validator

            mock_session = MagicMock()
            mock_user_result = MagicMock()
            mock_user_result.scalar.return_value = 1
            mock_cabinet_result = MagicMock()
            mock_cabinet_result.scalar.return_value = mock_wb_user_cabinet
            mock_no_token_result = MagicMock()
            mock_no_token_result.scalar.return_value = None
            mock_existing_token_result = MagicMock()
            mock_existing_token_result.scalar.return_value = mock_existing_token
            mock_session.execute = AsyncMock(
                side_effect=[
                    mock_user_result,
                    mock_cabinet_result,
                    mock_no_token_result,
                    mock_existing_token_result,
                ]
            )
            mock_session.commit = AsyncMock(side_effect=_build_integrity_error())
            mock_session.rollback = AsyncMock()
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock()

            await process_add_new_token(
                mock_message, mock_bot, mock_state, mock_client_session
            )

            mock_session.rollback.assert_awaited_once()
            mock_duplicate_helper.assert_awaited_once_with(
                bot=mock_bot,
                state=mock_state,
                chat_id=111111,
                current_user_id=1,
                current_user_telegram_id=1,
                existing_token=mock_existing_token,
                wb_user_cabinet_original_id=1,
            )

    @pytest.mark.asyncio
    async def test_duplicate_token_integrity_error_other_user_not_admin_hides_shop(
        self, mock_bot, mock_state, mock_client_session, mock_wb_user_cabinet
    ):
        """IntegrityError fallback for foreign token still must not reveal the shop."""
        good_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzc2OTk4Mjg4LCJpZCI6IjAxOWExMTgxLTc3ZjctNzA0Ni05ZmVkLTBkYWZiMTEzYjA5NSIsImlpZCI6NTQyNTkzMjQsIm9pZCI6NDA3OTM0OSwicyI6NzAsInNpZCI6IjI0YTk4OWVlLTM5Y2ItNDZjOC1hYzNmLWE4MzM3MGQ5NTg1ZiIsInQiOmZhbHNlLCJ1aWQiOjU0MjU5MzI0fQ.jFYQHctVOvRKSVz67O0WiLO7TrF-Z1YfYGcxbBmll8VQAEBjP-LsmigOk74HQfuvWSdDCNqcaQ0DizT-vXSkHA"
        shop_id = WBToken(api_key=good_token).get_shop_id_from_token()
        mock_wb_user_cabinet.wb_cabinet.shop_id = shop_id
        mock_message = _build_token_process_message(1, 111111, good_token)
        mock_existing_token = MagicMock(spec=WBToken)
        mock_existing_token.user_id = 999

        with (
            patch(
                "app.client_bot.user_interface.handlers.start.start.TokenPermissionsValidator"
            ) as mock_validator_class,
            patch("app.client_bot.user_interface.handlers.start.start.sm") as mock_sm,
            patch(
                "app.client_bot.user_interface.handlers.start.start.is_bot_admin",
                return_value=False,
            ),
            patch(
                "app.client_bot.user_interface.handlers.start.start._handle_duplicate_token_for_existing_shop",
                wraps=process_add_new_token.__globals__["_handle_duplicate_token_for_existing_shop"],
            ) as mock_duplicate_helper,
            patch("app.client_bot.user_interface.handlers.start.start.ShopMenu") as mock_shop_menu_ctor,
        ):
            mock_validator = MagicMock()
            mock_validator.validate = AsyncMock(
                return_value=_build_validation_result(shop_id)
            )
            mock_validator_class.return_value = mock_validator

            mock_session = MagicMock()
            mock_user_result = MagicMock()
            mock_user_result.scalar.return_value = 1
            mock_cabinet_result = MagicMock()
            mock_cabinet_result.scalar.return_value = mock_wb_user_cabinet
            mock_no_token_result = MagicMock()
            mock_no_token_result.scalar.return_value = None
            mock_existing_token_result = MagicMock()
            mock_existing_token_result.scalar.return_value = mock_existing_token
            mock_session.execute = AsyncMock(
                side_effect=[
                    mock_user_result,
                    mock_cabinet_result,
                    mock_no_token_result,
                    mock_existing_token_result,
                ]
            )
            mock_session.commit = AsyncMock(side_effect=_build_integrity_error())
            mock_session.rollback = AsyncMock()
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock()

            await process_add_new_token(
                mock_message, mock_bot, mock_state, mock_client_session
            )

            mock_session.rollback.assert_awaited_once()
            assert mock_duplicate_helper.await_count == 1
            mock_bot.send_message.assert_awaited_once_with(
                111111, DUPLICATE_TOKEN_MESSAGE
            )
            mock_state.clear.assert_not_called()
            mock_shop_menu_ctor.assert_not_called()
