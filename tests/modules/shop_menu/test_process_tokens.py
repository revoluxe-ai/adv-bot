import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.shop_menu.message import ShopMenu
from app.modules.common_slaves.wildberries.models import WBToken
from app.utils.db.models import User
from app.client_bot import const


class TestProcessTokens:
    @pytest.fixture
    def mock_bot(self):
        return AsyncMock()

    @pytest.fixture
    def mock_state(self):
        state = AsyncMock()
        state.update_data = AsyncMock()
        return state

    @pytest.fixture
    def sample_user(self):
        user = MagicMock(spec=User)
        user.user_telegram_id = 123456789
        return user

    @pytest.fixture
    def sample_wb_cabinet(self):
        wb_cabinet = MagicMock()
        wb_cabinet.id = 1
        wb_cabinet.shop_id = "test_shop_123"
        return wb_cabinet

    @pytest.fixture
    def sample_wb_user_cabinet(self, sample_user, sample_wb_cabinet):
        wb_user_cabinet = MagicMock()
        wb_user_cabinet.id = 1
        wb_user_cabinet.name = "Test Shop"
        wb_user_cabinet.user = sample_user
        wb_user_cabinet.wb_cabinet = sample_wb_cabinet
        return wb_user_cabinet

    @pytest.fixture
    def sample_shop_menu(self, mock_bot, mock_state, sample_wb_user_cabinet):
        shop_menu = ShopMenu(
            bot=mock_bot,
            chat_id=sample_wb_user_cabinet.user.user_telegram_id,
            state=mock_state,
            wb_user_cabinet_original_id=sample_wb_user_cabinet.id,
        )
        shop_menu._wb_user_cabinet = sample_wb_user_cabinet
        shop_menu._wb_cabinet = sample_wb_user_cabinet.wb_cabinet
        return shop_menu

    @pytest.mark.asyncio
    async def test_process_tokens_success(self, sample_shop_menu):
        """Test successful token processing for a shop."""
        mock_token = MagicMock(spec=WBToken)
        mock_token.expires = datetime.datetime.now() + datetime.timedelta(
            days=10, hours=1
        )

        with patch("app.modules.shop_menu.message.sm") as mock_sm:
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_token]
            mock_session.execute.return_value = mock_result

            result = await sample_shop_menu._process_tokens()

            assert result is True
            assert sample_shop_menu.last_days_for_token == 10
            sample_shop_menu.bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_tokens_no_tokens_not_admin(self, sample_shop_menu):
        """Test token processing when no tokens are found for a non-admin user."""
        with patch("app.modules.shop_menu.message.sm") as mock_sm:
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []  # No tokens
            mock_session.execute.return_value = mock_result

            # Ensure user is not an admin
            with patch("app.client_bot.const.ADMINS", new=[]):
                result = await sample_shop_menu._process_tokens()

                assert result is False
                sample_shop_menu.bot.send_message.assert_called_once()
                assert (
                    "Не найдены токены для этого магазина."
                    in sample_shop_menu.bot.send_message.call_args[0][1]
                )

    @pytest.mark.asyncio
    async def test_process_tokens_no_tokens_admin(self, sample_shop_menu):
        """Test token processing when no tokens are found for an admin user."""
        with patch("app.modules.shop_menu.message.sm") as mock_sm:
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []  # No tokens
            mock_session.execute.return_value = mock_result

            # Ensure user is an admin
            with patch(
                "app.client_bot.const.ADMINS", new=[sample_shop_menu._user_telegram_id]
            ):
                result = await sample_shop_menu._process_tokens()

                assert result is True
                assert (
                    sample_shop_menu.last_days_for_token == 30
                )  # Admin gets temporary token
                sample_shop_menu.bot.send_message.assert_not_called()
