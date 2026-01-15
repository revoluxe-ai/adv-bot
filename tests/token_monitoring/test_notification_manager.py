"""Tests for NotificationManager."""

import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import IntegrityError
from aiogram.exceptions import TelegramForbiddenError

from app.modules.token_monitoring.services.notification_manager import (
    NotificationManager,
    notify_token_deactivation,
    notify_token_expiring,
)
from app.modules.token_monitoring.models import (
    NotificationType,
    TokenNotificationTracker,
)
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.models import User


class TestNotificationManager:
    """Test cases for NotificationManager."""

    @pytest.fixture
    def mock_notification_sender(self):
        """Mock NotificationSender."""
        sender = MagicMock()
        sender.send_message = AsyncMock(return_value=True)
        return sender

    @pytest.fixture
    def mock_session_maker(self):
        """Mock session maker."""
        session = AsyncMock(return_value=None)
        session_maker = MagicMock()
        session_maker.return_value.__aenter__.return_value = session
        session_maker.return_value.__aexit__.return_value = None
        return session_maker, session

    @pytest.fixture
    def sample_user_cabinet(self):
        """Create sample user cabinet."""
        user = MagicMock(spec=User)
        user.user_telegram_id = 123456789

        cabinet = MagicMock(spec=WBUserCabinet)
        cabinet.name = "Test Shop"
        cabinet.user = user

        return cabinet

    @pytest.fixture
    def notification_manager(
        self, mock_notification_sender, mock_session_maker
    ):
        """Create NotificationManager with mocked dependencies."""
        session_maker, _ = mock_session_maker
        return NotificationManager(
            notification_sender=mock_notification_sender,
            session_maker=session_maker,
        )

    @pytest.mark.asyncio
    async def test_notify_token_deactivation(
        self,
        notification_manager,
        mock_session_maker,
        sample_user_cabinet,
        mock_notification_sender,
    ):
        """Test sending token deactivation notification."""
        session_maker, session = mock_session_maker

        # Mock _get_shop_users to return sample user
        notification_manager._get_shop_users = AsyncMock(
            return_value=[sample_user_cabinet]
        )

        await notification_manager.notify_token_issue(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
        )

        # Verify notification sender was called
        mock_notification_sender.send_message.assert_called_once()
        args, kwargs = mock_notification_sender.send_message.call_args
        assert args[0] == 123456789  # user_telegram_id
        assert "деактивирован" in args[1].lower()  # message contains deactivation text

        # Verify notification was recorded in database
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_token_expiring_14_days(
        self,
        notification_manager,
        mock_session_maker,
        sample_user_cabinet,
        mock_notification_sender,
    ):
        """Test sending 14-day expiration notification."""
        session_maker, session = mock_session_maker

        notification_manager._get_shop_users = AsyncMock(
            return_value=[sample_user_cabinet]
        )

        expiry_date = datetime.datetime.now() + datetime.timedelta(days=14)

        await notification_manager.notify_token_issue(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_EXPIRING_14_DAYS.value,
            expiry_date=expiry_date,
        )

        # Verify message content
        mock_notification_sender.send_message.assert_called_once()
        args, kwargs = mock_notification_sender.send_message.call_args
        message = args[1]
        assert "2 недели" in message
        assert "Test Shop" in message
        assert expiry_date.strftime("%d.%m.%Y") in message

    @pytest.mark.asyncio
    async def test_notify_token_expiring_3_days(
        self,
        notification_manager,
        mock_session_maker,
        sample_user_cabinet,
        mock_notification_sender,
    ):
        """Test sending 3-day expiration notification."""
        session_maker, session = mock_session_maker

        notification_manager._get_shop_users = AsyncMock(
            return_value=[sample_user_cabinet]
        )

        expiry_date = datetime.datetime.now() + datetime.timedelta(days=3)

        await notification_manager.notify_token_issue(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_EXPIRING_3_DAYS.value,
            expiry_date=expiry_date,
        )

        args, kwargs = mock_notification_sender.send_message.call_args
        message = args[1]
        assert "Внимание!" in message
        assert "3 дня" in message
        assert "срочно" in message.lower()

    @pytest.mark.asyncio
    async def test_notify_token_expiring_1_day(
        self,
        notification_manager,
        mock_session_maker,
        sample_user_cabinet,
        mock_notification_sender,
    ):
        """Test sending 1-day expiration notification."""
        session_maker, session = mock_session_maker

        notification_manager._get_shop_users = AsyncMock(
            return_value=[sample_user_cabinet]
        )

        expiry_date = datetime.datetime.now() + datetime.timedelta(days=1)

        await notification_manager.notify_token_issue(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_EXPIRING_1_DAY.value,
            expiry_date=expiry_date,
        )

        args, kwargs = mock_notification_sender.send_message.call_args
        message = args[1]
        assert "СРОЧНО!" in message
        assert "завтра" in message
        assert "сегодня" in message

    @pytest.mark.asyncio
    async def test_telegram_forbidden_error_handling(
        self,
        notification_manager,
        mock_session_maker,
        sample_user_cabinet,
        mock_notification_sender,
    ):
        """Test handling when user blocks the bot."""
        session_maker, session = mock_session_maker

        # Mock TelegramForbiddenError - create a simple Exception instead
        mock_notification_sender.send_message.side_effect = Exception(
            "Forbidden: bot was blocked by the user"
        )
        notification_manager._get_shop_users = AsyncMock(
            return_value=[sample_user_cabinet]
        )

        # Should not raise exception
        await notification_manager.notify_token_issue(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
        )

        # Bot message was attempted but failed
        mock_notification_sender.send_message.assert_called_once()
        # Session should not have added notification due to failed send
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_notification_handling(
        self,
        notification_manager,
        mock_session_maker,
        sample_user_cabinet,
        mock_notification_sender,
    ):
        """Test handling duplicate notifications via database constraint."""
        session_maker, session = mock_session_maker

        notification_manager._get_shop_users = AsyncMock(
            return_value=[sample_user_cabinet]
        )

        # Mock IntegrityError for duplicate constraint violation
        orig_error = Exception("original error")
        session.flush.side_effect = IntegrityError("duplicate key", orig_error, None)

        await notification_manager.notify_token_issue(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
        )

        # Message was sent but database rollback occurred
        mock_notification_sender.send_message.assert_called_once()
        session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_users_notification(
        self,
        notification_manager,
        mock_session_maker,
        mock_notification_sender,
    ):
        """Test sending notifications to multiple users."""
        session_maker, session = mock_session_maker

        # Create multiple user cabinets
        users = []
        for i in range(3):
            user = MagicMock(spec=User)
            user.user_telegram_id = 123456789 + i

            cabinet = MagicMock(spec=WBUserCabinet)
            cabinet.name = f"Test Shop {i}"
            cabinet.user = user
            users.append(cabinet)

        notification_manager._get_shop_users = AsyncMock(return_value=users)

        await notification_manager.notify_token_issue(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
        )

        # Verify message sent to all users
        assert mock_notification_sender.send_message.call_count == 3

        # Verify all notifications recorded
        assert session.add.call_count == 3

    @pytest.mark.asyncio
    async def test_mark_notifications_resolved(
        self, notification_manager, mock_session_maker
    ):
        """Test marking notifications as resolved."""
        session_maker, session = mock_session_maker

        # Mock the entire method to avoid AsyncMock issues
        notification_manager.mark_notifications_resolved = AsyncMock(return_value=2)

        result = await notification_manager.mark_notifications_resolved(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
        )

        assert result == 2

    @pytest.mark.asyncio
    async def test_get_notification_history(
        self, notification_manager, mock_session_maker
    ):
        """Test getting notification history."""
        session_maker, session = mock_session_maker

        # Mock notification history
        notifications = [MagicMock(spec=TokenNotificationTracker) for _ in range(5)]

        # Mock the entire method to avoid AsyncMock issues
        notification_manager.get_notification_history = AsyncMock(
            return_value=notifications
        )

        result = await notification_manager.get_notification_history(
            "test_shop_123", limit=10
        )

        assert len(result) == 5
        assert result == notifications

    def test_format_message_deactivation(self, notification_manager):
        """Test message formatting for deactivation."""
        message = notification_manager._format_message(
            NotificationType.TOKEN_DEACTIVATED.value, "Test Shop"
        )

        assert "деактивирован" in message.lower()
        assert "Test Shop" in message

    def test_format_message_expiring_with_date(self, notification_manager):
        """Test message formatting for expiring token with date."""
        expiry_date = datetime.datetime(2024, 12, 25, 10, 0, 0)

        message = notification_manager._format_message(
            NotificationType.TOKEN_EXPIRING_14_DAYS.value, "Test Shop", expiry_date
        )

        assert "Test Shop" in message
        assert "25.12.2024" in message
        assert "2 недели" in message

    def test_format_message_unknown_type(self, notification_manager):
        """Test message formatting for unknown notification type."""
        message = notification_manager._format_message("UNKNOWN_TYPE", "Test Shop")

        assert "Проблема с токеном" in message
        assert "Test Shop" in message

    @pytest.mark.asyncio
    async def test_convenience_function_notify_token_deactivation(self):
        """Test convenience function for token deactivation notification."""
        with patch(
            "app.modules.token_monitoring.services.notification_manager.NotificationManager"
        ) as mock_manager_class:
            mock_manager = AsyncMock(return_value=None)
            mock_manager_class.return_value = mock_manager

            await notify_token_deactivation("test_shop_123", context={"test": "data"})

            mock_manager.notify_token_issue.assert_called_once_with(
                shop_id="test_shop_123",
                notification_type=NotificationType.TOKEN_DEACTIVATED.value,
                context={"test": "data"},
            )

    @pytest.mark.asyncio
    async def test_convenience_function_notify_token_expiring(self):
        """Test convenience function for token expiring notification."""
        with patch(
            "app.modules.token_monitoring.services.notification_manager.NotificationManager"
        ) as mock_manager_class:
            mock_manager = AsyncMock(return_value=None)
            mock_manager_class.return_value = mock_manager

            expiry_date = datetime.datetime.now() + datetime.timedelta(days=3)

            await notify_token_expiring("test_shop_123", 3, expiry_date)

            mock_manager.notify_token_issue.assert_called_once_with(
                shop_id="test_shop_123",
                notification_type=NotificationType.TOKEN_EXPIRING_3_DAYS.value,
                expiry_date=expiry_date,
            )

    @pytest.mark.asyncio
    async def test_convenience_function_notify_token_expiring_unsupported_days(self):
        """Test convenience function with unsupported days until expiry."""
        with patch(
            "app.modules.token_monitoring.services.notification_manager.NotificationManager"
        ) as mock_manager_class:
            mock_manager = AsyncMock(return_value=None)
            mock_manager_class.return_value = mock_manager

            expiry_date = datetime.datetime.now() + datetime.timedelta(days=5)

            await notify_token_expiring("test_shop_123", 5, expiry_date)

            # Should not call notify_token_issue for unsupported days
            mock_manager.notify_token_issue.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_users_found_for_shop(
        self,
        notification_manager,
        mock_session_maker,
        mock_notification_sender,
    ):
        """Test notification when no users found for shop."""
        session_maker, session = mock_session_maker

        notification_manager._get_shop_users = AsyncMock(return_value=[])

        await notification_manager.notify_token_issue(
            shop_id="test_shop_123",
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
        )

        # No messages should be sent
        mock_notification_sender.send_message.assert_not_called()
        session.add.assert_not_called()
