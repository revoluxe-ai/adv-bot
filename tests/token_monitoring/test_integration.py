"""Integration tests for token monitoring system."""

import asyncio
import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.token_monitoring import (
    initialize_token_monitoring,
    shutdown_token_monitoring,
    TokenInfoService,
    NotificationManager,
    TokenExpirationService,
    TokenMonitoringScheduler,
)
from app.modules.token_monitoring.models import NotificationType
from app.modules.token_monitoring.integration import TokenMonitoringIntegration
from app.utils.db.models import User
from app.modules.common_slaves.wildberries.models import WBUserCabinet


class TestTokenMonitoringIntegration:
    """Integration tests for the complete token monitoring system."""

    @pytest.fixture
    def mock_session_maker(self):
        """Mock session maker for database operations."""
        session = AsyncMock(return_value=None)
        session.execute = AsyncMock(return_value=None)
        session.add = AsyncMock(return_value=None)
        session.commit = AsyncMock(return_value=None)
        session_maker = MagicMock()
        session_maker.return_value.__aenter__.return_value = session
        session_maker.return_value.__aexit__.return_value = None
        return session_maker, session

    @pytest.fixture
    def mock_bot(self):
        """Mock Telegram bot."""
        bot = AsyncMock(return_value=None)
        bot.send_message = AsyncMock(return_value=None)
        return bot

    @pytest.mark.asyncio
    async def test_complete_system_initialization(self):
        """Test complete system initialization and shutdown."""
        with patch(
            "app.modules.token_monitoring.startup.install_token_monitoring",
            new_callable=MagicMock,
        ) as mock_install:
            with patch(
                "app.modules.token_monitoring.startup.start_token_monitoring_scheduler"
            ) as mock_scheduler:
                # Test initialization
                await initialize_token_monitoring(
                    enable_decorator_monitoring=True, enable_expiration_scheduler=True
                )

                # Verify components were initialized
                mock_install.assert_called_once()
                mock_scheduler.assert_called_once()

        with patch(
            "app.modules.token_monitoring.scheduler.stop_token_monitoring_scheduler"
        ) as mock_stop_scheduler:
            with patch(
                "app.modules.token_monitoring.integration.uninstall_token_monitoring"
            ) as mock_uninstall:
                # Test shutdown
                await shutdown_token_monitoring()

                # Verify components were shut down
                mock_stop_scheduler.assert_called_once()
                mock_uninstall.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_deactivation_end_to_end_workflow(
        self, mock_session_maker, mock_bot
    ):
        """Test complete token deactivation detection and notification workflow."""
        session_maker, session = mock_session_maker

        # Create integrated components
        notification_manager = NotificationManager(
            bot=mock_bot, session_maker=session_maker
        )

        # Mock user data

        user = MagicMock(spec=User)
        user.user_telegram_id = 123456789

        user_cabinet = MagicMock(spec=WBUserCabinet)
        user_cabinet.name = "Test Shop"
        user_cabinet.user = user

        # Mock _get_shop_users to return our test user
        notification_manager._get_shop_users = AsyncMock(return_value=[user_cabinet])

        # Simulate token deactivation event
        shop_id = "test_shop_123"

        # This would normally be triggered by the HTTP decorator
        await notification_manager.notify_token_issue(
            shop_id=shop_id,
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
            context={"method_name": "get_advs", "error": "All tokens failed"},
        )

        # Verify notification was sent
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args

        assert args[0] == 123456789  # user_telegram_id
        assert "деактивирован" in args[1].lower()
        assert "Test Shop" in args[1]

        # Verify database record was created
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_expiration_monitoring_workflow(
        self, mock_session_maker, mock_bot
    ):
        """Test complete token expiration monitoring workflow."""
        session_maker, session = mock_session_maker

        # Create integrated components
        notification_manager = NotificationManager(
            bot=mock_bot, session_maker=session_maker
        )
        expiration_service = TokenExpirationService(
            notification_manager=notification_manager, session_maker=session_maker
        )

        # Mock token expiring in 14 days
        from app.modules.common_slaves.wildberries.models import WBToken

        expiring_token = MagicMock(spec=WBToken)
        expiring_token.id = 1
        expiring_token.shop_id = "test_shop_123"
        fixed_now = datetime.datetime(2025, 10, 15, 9, 0, 0)
        expiring_token.expires = fixed_now + datetime.timedelta(days=14)
        expiring_token.categories = {"Контент", "Статистика"}
        expiring_token.read_only = False
        expiring_token.check_valid.return_value = True

        # Mock user data
        from app.utils.db.models import User

        user = MagicMock(spec=User)
        user.user_telegram_id = 123456789

        user_cabinet = MagicMock(spec=WBUserCabinet)
        user_cabinet.name = "Test Shop"
        user_cabinet.user = user

        # Mock database queries
        expiration_service._get_active_tokens_with_expiry = AsyncMock(
            return_value=[expiring_token]
        )
        expiration_service._notification_already_sent = AsyncMock(return_value=False)
        notification_manager._get_shop_users = AsyncMock(return_value=[user_cabinet])

        with patch(
            "datetime.datetime", MagicMock(now=MagicMock(return_value=fixed_now))
        ):
            # Run expiration check
            stats = await expiration_service.check_token_expiration()

            # Verify results
            assert stats["total_tokens_checked"] == 1
            assert stats["expiring_tokens_found"] == 1
            assert stats["notifications_sent"] == 1
            assert stats["warnings_by_stage"][14] == 1

            # Verify notification was sent
            mock_bot.send_message.assert_called_once()
            args, kwargs = mock_bot.send_message.call_args

            assert args[0] == 123456789
            assert "2 недели" in args[1]
            assert "Test Shop" in args[1]

    @pytest.mark.asyncio
    async def test_token_info_service_integration(self, mock_session_maker):
        """Test TokenInfoService integration with real data flow."""
        session_maker, session = mock_session_maker

        # Create service
        token_info_service = TokenInfoService(session_maker=session_maker)

        # Mock tokens with different states
        from app.modules.common_slaves.wildberries.models import WBToken

        valid_token = MagicMock(spec=WBToken)
        valid_token.id = 1
        valid_token.api_key = "valid_key"
        valid_token.user_id = 123
        valid_token.shop_id = "test_shop_123"
        valid_token.expires = datetime.datetime.now() + datetime.timedelta(days=30)
        valid_token.categories = {"Контент", "Статистика", "Аналитика", "Продвижение"}
        valid_token.read_only = False
        valid_token.check_valid.return_value = True

        expired_token = MagicMock(spec=WBToken)
        expired_token.id = 2
        expired_token.api_key = "expired_key"
        expired_token.user_id = 123
        expired_token.shop_id = "test_shop_123"
        expired_token.expires = datetime.datetime.now() - datetime.timedelta(days=1)
        expired_token.categories = {"Контент"}
        expired_token.read_only = False
        expired_token.check_valid.return_value = False

        # Mock database queries
        # First call to execute - get tokens
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [valid_token, expired_token]
        mock_result_tokens = MagicMock()
        mock_result_tokens.scalars.return_value = mock_scalars

        # Second call to execute - get shop name
        mock_result_shop = MagicMock()
        mock_result_shop.scalar.return_value = "Test Shop"

        session.execute = AsyncMock(side_effect=[mock_result_tokens, mock_result_shop])

        # Mock _get_expiring_tokens
        token_info_service._get_expiring_tokens = AsyncMock(return_value=[])

        # Get token status
        status_report = await token_info_service.get_shop_token_status("test_shop_123")

        # Verify complete status analysis
        assert status_report.shop_id == "test_shop_123"
        assert status_report.shop_name == "Test Shop"
        assert (
            status_report.status == "Complete"
        )  # Valid token has all required permissions
        assert status_report.total_tokens == 2
        assert status_report.valid_token_count == 1
        assert len(status_report.expired_tokens) == 1
        assert status_report.has_all_required_permissions

    @pytest.mark.asyncio
    async def test_scheduler_integration(self, mock_session_maker, mock_bot):
        """Test scheduler integration with expiration service."""
        session_maker, session = mock_session_maker

        # Create integrated components
        notification_manager = NotificationManager(
            bot=mock_bot, session_maker=session_maker
        )
        expiration_service = TokenExpirationService(
            notification_manager=notification_manager, session_maker=session_maker
        )
        scheduler = TokenMonitoringScheduler(
            expiration_service=expiration_service,
            notification_manager=notification_manager,
        )

        # Mock expiration check
        expiration_service.check_token_expiration = AsyncMock(
            return_value={
                "total_tokens_checked": 5,
                "notifications_sent": 2,
                "errors": 0,
            }
        )

        # Run manual check
        stats = await scheduler.run_manual_check()

        assert stats["total_tokens_checked"] == 5
        assert stats["notifications_sent"] == 2
        assert stats["errors"] == 0

        # Verify expiration service was called
        expiration_service.check_token_expiration.assert_called_once()

    def test_integration_installation_and_removal(self):
        """Test installation and removal of token monitoring integration."""
        integration = TokenMonitoringIntegration()

        # Mock the http_request module
        with patch("app.core.wb_api.http_request") as mock_http_module:
            mock_original_decorator = MagicMock()
            mock_http_module.try_except_decorator = mock_original_decorator

            # Test installation
            integration.install()

            assert integration.is_installed
            assert integration._original_decorator == mock_original_decorator
            # Verify decorator was replaced
            assert mock_http_module.try_except_decorator != mock_original_decorator

            # Test uninstallation
            integration.uninstall()

            assert not integration.is_installed
            assert mock_http_module.try_except_decorator == mock_original_decorator

    @pytest.mark.asyncio
    async def test_error_handling_in_integration(self, mock_session_maker, mock_bot):
        """Test error handling across integrated components."""
        session_maker, session = mock_session_maker

        # Create components
        notification_manager = NotificationManager(
            bot=mock_bot, session_maker=session_maker
        )

        # Mock bot to raise exception
        from aiogram.exceptions import TelegramForbiddenError

        mock_bot.send_message.side_effect = TelegramForbiddenError(
            message="User blocked bot", method="test_method"
        )

        # Mock user data
        user = MagicMock(spec=User)
        user.user_telegram_id = 123456789

        user_cabinet = MagicMock(spec=WBUserCabinet)
        user_cabinet.name = "Test Shop"
        user_cabinet.user = user

        notification_manager._get_shop_users = AsyncMock(return_value=[user_cabinet])

        # Should not raise exception despite bot error
        await notification_manager.notify_token_issue(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
        )

        # Bot was called but notification was not recorded due to error
        mock_bot.send_message.assert_called_once()
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_notification_prevention(
        self, mock_session_maker, mock_bot
    ):
        """Test prevention of duplicate notifications."""
        from sqlalchemy.exc import IntegrityError

        session_maker, session = mock_session_maker

        notification_manager = NotificationManager(
            bot=mock_bot, session_maker=session_maker
        )

        # Mock user data
        user = MagicMock(spec=User)
        user.user_telegram_id = 123456789

        user_cabinet = MagicMock(spec=WBUserCabinet)
        user_cabinet.name = "Test Shop"
        user_cabinet.user = user

        notification_manager._get_shop_users = AsyncMock(return_value=[user_cabinet])

        # Mock database constraint violation
        session.flush.side_effect = IntegrityError("duplicate key", "orig", "params")

        # Should handle duplicate gracefully
        await notification_manager.notify_token_issue(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
        )

        # Message was sent but database rolled back
        mock_bot.send_message.assert_called_once()
        session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_warning_stages_integration(
        self, mock_session_maker, mock_bot
    ):
        """Test multiple warning stages in a single expiration check."""
        session_maker, session = mock_session_maker

        # Create components
        notification_manager = NotificationManager(
            bot=mock_bot, session_maker=session_maker
        )
        expiration_service = TokenExpirationService(
            notification_manager=notification_manager, session_maker=session_maker
        )

        # Mock tokens at different warning stages
        from app.modules.common_slaves.wildberries.models import WBToken

        fixed_now = datetime.datetime(2025, 10, 15, 9, 0, 0)
        tokens = []
        for days, shop_suffix in [(14, "shop1"), (3, "shop2"), (1, "shop3")]:
            token = MagicMock(spec=WBToken)
            token.id = days
            token.shop_id = f"test_{shop_suffix}"
            token.expires = fixed_now + datetime.timedelta(days=days)
            token.categories = {"Контент"}
            token.read_only = False
            token.check_valid.return_value = True
            tokens.append(token)

        # Mock user data for each shop
        user_cabinets = []
        for i, shop_suffix in enumerate(["shop1", "shop2", "shop3"]):
            user = MagicMock(spec=User)
            user.user_telegram_id = 123456789 + i

            cabinet = MagicMock(spec=WBUserCabinet)
            cabinet.name = f"Test {shop_suffix}"
            cabinet.user = user
            user_cabinets.append([cabinet])

        # Mock database and service methods
        expiration_service._get_active_tokens_with_expiry = AsyncMock(
            return_value=tokens
        )
        expiration_service._notification_already_sent = AsyncMock(return_value=False)
        notification_manager._get_shop_users = AsyncMock(side_effect=user_cabinets)

        with patch(
            "datetime.datetime", MagicMock(now=MagicMock(return_value=fixed_now))
        ):
            # Run expiration check
            stats = await expiration_service.check_token_expiration()

            # Verify all warning stages were processed
            assert stats["total_tokens_checked"] == 3
            assert stats["expiring_tokens_found"] == 3
            assert stats["notifications_sent"] == 3
            assert stats["warnings_by_stage"][14] == 1
            assert stats["warnings_by_stage"][3] == 1
            assert stats["warnings_by_stage"][1] == 1

            # Verify all notifications were sent
            assert mock_bot.send_message.call_count == 3
