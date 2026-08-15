"""
Comprehensive tests for the add_new_token handler in start.py
Tests cover all workflow scenarios and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User as TelegramUser
from aiogram.fsm.context import FSMContext

from app.client_bot.user_interface.handlers.start.start import (
    process_add_new_token,
    process_cabinet_api,
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
        self, mock_bot, mock_state, mock_client_session
    ):
        """Test handler when token already exists for the same user"""
        good_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzc2OTk4Mjg4LCJpZCI6IjAxOWExMTgxLTc3ZjctNzA0Ni05ZmVkLTBkYWZiMTEzYjA5NSIsImlpZCI6NTQyNTkzMjQsIm9pZCI6NDA3OTM0OSwicyI6NzAsInNpZCI6IjI0YTk4OWVlLTM5Y2ItNDZjOC1hYzNmLWE4MzM3MGQ5NTg1ZiIsInQiOmZhbHNlLCJ1aWQiOjU0MjU5MzI0fQ.jFYQHctVOvRKSVz67O0WiLO7TrF-Z1YfYGcxbBmll8VQAEBjP-LsmigOk74HQfuvWSdDCNqcaQ0DizT-vXSkHA"
        shop_id = WBToken(api_key=good_token).get_shop_id_from_token()
        # Mock WBToken instance instead of creating a real one
        mock_token_instance = MagicMock(spec=WBToken)
        mock_token_instance.shop_id = shop_id
        mock_token_instance.user_id = 1
        mock_token_instance.api_key = good_token
        mock_token_instance.get_shop_id_from_token.return_value = "test-shop-id-001"
        mock_token_instance.read_only = False
        mock_token_instance.is_expired = False
        mock_token_instance.categories = ["Статистика"]

        mock_message = MagicMock(spec=Message)
        mock_user = MagicMock()
        mock_user.id = 1
        mock_message.from_user = mock_user
        mock_chat = MagicMock()
        mock_chat.id = 111111
        mock_message.chat = mock_chat

        mock_message.text = good_token

        with patch(
            "app.client_bot.user_interface.handlers.start.start.TokenPermissionsValidator"
        ) as mock_validator_class:
            mock_validator = MagicMock()
            mock_result = MagicMock()
            mock_result.is_valid_jwt = True
            mock_result.is_personal = True
            mock_result.is_read_only = False
            mock_result.is_expired = False
            mock_result.can_be_used_for_free = True
            mock_result.shop_id = shop_id
            mock_validator.validate = AsyncMock(return_value=mock_result)
            mock_validator_class.return_value = mock_validator

            with (
                patch("app.client_bot.user_interface.handlers.start.start.sm") as mock_sm,
                patch(
                    "app.client_bot.user_interface.handlers.start.start._open_existing_user_cabinet_by_shop_id",
                    AsyncMock(return_value=True),
                ) as mock_open_existing_cabinet,
            ):
                mock_session = MagicMock()

                # Handler uses Result.scalar_one_or_none() (not scalar()).
                # First query - user found
                mock_user_result = MagicMock()
                mock_user_result.scalar_one_or_none.return_value = 1

                mock_wb_user_cabinet = MagicMock(spec=WBUserCabinet)
                mock_wb_user_cabinet.id = 1
                mock_wb_user_cabinet.wb_cabinet = MagicMock(spec=WBCabinet)
                mock_wb_user_cabinet.wb_cabinet.shop_id = shop_id
                # Second query - cabinet found (shop_id must match validation_result)
                mock_cabinet_result = MagicMock()
                mock_cabinet_result.scalar_one_or_none.return_value = (
                    mock_wb_user_cabinet
                )

                # Third query - existing token found for same user
                mock_existing_token = MagicMock(spec=WBToken)
                mock_existing_token.user_id = 1
                mock_existing_token.api_key = good_token
                mock_existing_token.get_shop_id_from_token = MagicMock()
                mock_existing_token.get_shop_id_from_token.return_value = shop_id
                mock_token_result = MagicMock()
                mock_token_result.scalar_one_or_none.return_value = mock_existing_token

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
                assert "Этот токен уже есть в системе." in call_args[0][1]
                mock_open_existing_cabinet.assert_awaited_once_with(
                    bot=mock_bot,
                    chat_id=111111,
                    state=mock_state,
                    user_id=1,
                    shop_id=shop_id,
                )

    @pytest.mark.asyncio
    async def test_duplicate_token_same_user_opens_existing_cabinet(
        self, mock_bot, mock_state, mock_client_session
    ) -> None:
        """Duplicate token path should reopen the existing cabinet instead of stopping."""
        good_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzc2OTk4Mjg4LCJpZCI6IjAxOWExMTgxLTc3ZjctNzA0Ni05ZmVkLTBkYWZiMTEzYjA5NSIsImlpZCI6NTQyNTkzMjQsIm9pZCI6NDA3OTM0OSwicyI6NzAsInNpZCI6IjI0YTk4OWVlLTM5Y2ItNDZjOC1hYzNmLWE4MzM3MGQ5NTg1ZiIsInQiOmZhbHNlLCJ1aWQiOjU0MjU5MzI0fQ.jFYQHctVOvRKSVz67O0WiLO7TrF-Z1YfYGcxbBmll8VQAEBjP-LsmigOk74HQfuvWSdDCNqcaQ0DizT-vXSkHA"
        shop_id = WBToken(api_key=good_token).get_shop_id_from_token()

        mock_message = MagicMock(spec=Message)
        mock_user = MagicMock()
        mock_user.id = 1
        mock_message.from_user = mock_user
        mock_chat = MagicMock()
        mock_chat.id = 111111
        mock_message.chat = mock_chat
        mock_message.text = good_token

        mock_state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})

        with patch(
            "app.client_bot.user_interface.handlers.start.start.TokenPermissionsValidator"
        ) as mock_validator_class:
            mock_validator = MagicMock()
            mock_result = MagicMock()
            mock_result.is_valid_jwt = True
            mock_result.is_personal = True
            mock_result.is_read_only = False
            mock_result.is_expired = False
            mock_result.can_be_used_for_free = True
            mock_result.shop_id = shop_id
            mock_validator.validate = AsyncMock(return_value=mock_result)
            mock_validator_class.return_value = mock_validator

            with (
                patch("app.client_bot.user_interface.handlers.start.start.sm") as mock_sm,
                patch(
                    "app.client_bot.user_interface.handlers.start.start._open_existing_user_cabinet_by_shop_id",
                    AsyncMock(return_value=True),
                ) as mock_open_existing_cabinet,
            ):
                session_user = MagicMock()
                user_result = MagicMock()
                user_result.scalar_one_or_none.return_value = 1
                session_user.execute = AsyncMock(return_value=user_result)

                session_wb_user_cabinet = MagicMock()
                existing_wb_user_cabinet = MagicMock(spec=WBUserCabinet)
                existing_wb_user_cabinet.id = 1
                existing_wb_user_cabinet.wb_cabinet = MagicMock(spec=WBCabinet)
                existing_wb_user_cabinet.wb_cabinet.shop_id = shop_id
                wb_user_cabinet_result = MagicMock()
                wb_user_cabinet_result.scalar_one_or_none.return_value = (
                    existing_wb_user_cabinet
                )
                session_wb_user_cabinet.execute = AsyncMock(
                    return_value=wb_user_cabinet_result
                )

                session_token = MagicMock()
                token_result = MagicMock()
                existing_token = MagicMock(spec=WBToken)
                existing_token.user_id = 1
                token_result.scalar_one_or_none.return_value = existing_token
                session_token.execute = AsyncMock(return_value=token_result)

                mock_sm.side_effect = [
                    MagicMock(
                        __aenter__=AsyncMock(return_value=session_user),
                        __aexit__=AsyncMock(return_value=None),
                    ),
                    MagicMock(
                        __aenter__=AsyncMock(return_value=session_wb_user_cabinet),
                        __aexit__=AsyncMock(return_value=None),
                    ),
                    MagicMock(
                        __aenter__=AsyncMock(return_value=session_token),
                        __aexit__=AsyncMock(return_value=None),
                    ),
                ]

                await process_add_new_token(
                    mock_message, mock_bot, mock_state, mock_client_session
                )

        mock_bot.send_message.assert_awaited()
        assert "Этот токен уже есть в системе." in mock_bot.send_message.await_args_list[0].args[1]
        mock_state.clear.assert_awaited_once()
        mock_open_existing_cabinet.assert_awaited_once_with(
            bot=mock_bot,
            chat_id=111111,
            state=mock_state,
            user_id=1,
            shop_id=shop_id,
        )

    @pytest.mark.asyncio
    async def test_duplicate_existing_cabinet_opens_shop_menu(
        self, mock_bot, mock_state, mock_client_session
    ) -> None:
        """Existing cabinet path should send the info message and then open ShopMenu."""
        good_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzc2OTk4Mjg4LCJpZCI6IjAxOWExMTgxLTc3ZjctNzA0Ni05ZmVkLTBkYWZiMTEzYjA5NSIsImlpZCI6NTQyNTkzMjQsIm9pZCI6NDA3OTM0OSwicyI6NzAsInNpZCI6IjI0YTk4OWVlLTM5Y2ItNDZjOC1hYzNmLWE4MzM3MGQ5NTg1ZiIsInQiOmZhbHNlLCJ1aWQiOjU0MjU5MzI0fQ.jFYQHctVOvRKSVz67O0WiLO7TrF-Z1YfYGcxbBmll8VQAEBjP-LsmigOk74HQfuvWSdDCNqcaQ0DizT-vXSkHA"
        shop_id = WBToken(api_key=good_token).get_shop_id_from_token()

        mock_message = MagicMock(spec=Message)
        mock_user = MagicMock()
        mock_user.id = 1
        mock_message.from_user = mock_user
        mock_chat = MagicMock()
        mock_chat.id = 111111
        mock_message.chat = mock_chat
        mock_message.text = good_token

        mock_state.get_data = AsyncMock(return_value={"cabinet_name": "Test Cabinet"})
        mock_state.update_data = AsyncMock()

        with patch(
            "app.client_bot.user_interface.handlers.start.start.TokenPermissionsValidator"
        ) as mock_validator_class:
            mock_validator = MagicMock()
            mock_result = MagicMock()
            mock_result.is_valid_jwt = True
            mock_result.is_personal = True
            mock_result.is_expired = False
            mock_result.can_be_used_for_free = True
            mock_result.shop_id = shop_id
            mock_validator.validate = AsyncMock(return_value=mock_result)
            mock_validator_class.return_value = mock_validator

            with (
                patch("app.client_bot.user_interface.handlers.start.start.sm") as mock_sm,
                patch(
                    "app.client_bot.user_interface.handlers.start.start.messages.ShopUpdateInfo",
                    MagicMock(return_value=AsyncMock()),
                ),
                patch(
                    "app.client_bot.user_interface.handlers.start.start.messages.CabinetExistsForUser",
                    MagicMock(return_value=AsyncMock()),
                ) as mock_cabinet_exists_ctor,
                patch(
                    "app.client_bot.user_interface.handlers.start.start.ShopMenu",
                    MagicMock(return_value=AsyncMock()),
                ) as mock_shop_menu_ctor,
            ):
                user_id_result = MagicMock()
                user_id_result.scalar_one_or_none.return_value = 1

                token_check_result = MagicMock()
                token_check_result.scalar_one_or_none.return_value = None

                existing_wb_cabinet = MagicMock(spec=WBCabinet)
                existing_wb_cabinet.id = 22
                existing_wb_cabinet.active = True
                existing_wb_cabinet.shop_id = shop_id
                cabinet_result = MagicMock()
                cabinet_result.scalar_one_or_none.return_value = existing_wb_cabinet

                existing_wb_user_cabinet = MagicMock(spec=WBUserCabinet)
                existing_wb_user_cabinet.id = 77
                wb_user_cabinet_result = MagicMock()
                wb_user_cabinet_result.scalar_one_or_none.return_value = (
                    existing_wb_user_cabinet
                )

                session_user = MagicMock()
                session_user.execute = AsyncMock(return_value=user_id_result)

                session_main = MagicMock()
                session_main.execute = AsyncMock(
                    side_effect=[
                        token_check_result,
                        cabinet_result,
                        wb_user_cabinet_result,
                    ]
                )
                session_main.flush = AsyncMock()
                session_main.commit = AsyncMock()

                mock_sm.side_effect = [
                    MagicMock(
                        __aenter__=AsyncMock(return_value=session_user),
                        __aexit__=AsyncMock(return_value=None),
                    ),
                    MagicMock(
                        __aenter__=AsyncMock(return_value=session_main),
                        __aexit__=AsyncMock(return_value=None),
                    ),
                ]

                await process_cabinet_api(
                    mock_message, mock_bot, mock_state, mock_client_session
                )

        mock_cabinet_exists_ctor.assert_called_once_with(mock_bot, 111111)
        mock_state.update_data.assert_awaited_once_with(
            last_wb_user_cabinet_original_id=77
        )
        mock_shop_menu_ctor.assert_called_once_with(mock_bot, 111111, mock_state, 77)
        mock_shop_menu_ctor.return_value.assert_awaited_once()
