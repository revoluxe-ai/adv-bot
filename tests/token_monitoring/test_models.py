"""Tests for token monitoring models."""

import datetime
import pytest

from app.modules.token_monitoring.models import (
    TokenNotificationTracker,
    NotificationType,
)


class TestTokenNotificationTracker:
    """Test cases for TokenNotificationTracker model."""

    def test_token_notification_tracker_creation(self):
        """Test creating a TokenNotificationTracker instance."""
        notification = TokenNotificationTracker(
            shop_id="test_shop_123",
            user_telegram_id=123456789,
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
            sent_at=datetime.datetime.utcnow(),
        )

        assert notification.shop_id == "test_shop_123"
        assert notification.user_telegram_id == 123456789
        assert (
            notification.notification_type == NotificationType.TOKEN_DEACTIVATED.value
        )
        assert notification.token_expiry_date is None
        assert notification.resolved_at is None
        assert not notification.is_resolved

    def test_token_notification_tracker_with_expiry_date(self):
        """Test creating a TokenNotificationTracker with expiry date."""
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=14)

        notification = TokenNotificationTracker(
            shop_id="test_shop_123",
            user_telegram_id=123456789,
            notification_type=NotificationType.TOKEN_EXPIRING_14_DAYS.value,
            token_expiry_date=expiry_date,
            sent_at=datetime.datetime.utcnow(),
        )

        assert notification.token_expiry_date == expiry_date
        assert (
            notification.notification_type
            == NotificationType.TOKEN_EXPIRING_14_DAYS.value
        )

    def test_mark_resolved(self):
        """Test marking notification as resolved."""
        notification = TokenNotificationTracker(
            shop_id="test_shop_123",
            user_telegram_id=123456789,
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
            sent_at=datetime.datetime.utcnow(),
        )

        assert not notification.is_resolved

        notification.mark_resolved()

        assert notification.is_resolved
        assert notification.resolved_at is not None
        assert isinstance(notification.resolved_at, datetime.datetime)

    def test_repr(self):
        """Test string representation of TokenNotificationTracker."""
        sent_at = datetime.datetime.utcnow()
        notification = TokenNotificationTracker(
            shop_id="test_shop_123",
            user_telegram_id=123456789,
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
            sent_at=sent_at,
        )

        repr_str = repr(notification)

        assert "TokenNotificationTracker" in repr_str
        assert "test_shop_123" in repr_str
        assert "123456789" in repr_str
        assert NotificationType.TOKEN_DEACTIVATED.value in repr_str


class TestNotificationType:
    """Test cases for NotificationType enum."""

    def test_notification_type_values(self):
        """Test NotificationType enum values."""
        assert NotificationType.TOKEN_DEACTIVATED.value == "TOKEN_DEACTIVATED"
        assert NotificationType.TOKEN_EXPIRING_14_DAYS.value == "TOKEN_EXPIRING_14_DAYS"
        assert NotificationType.TOKEN_EXPIRING_3_DAYS.value == "TOKEN_EXPIRING_3_DAYS"
        assert NotificationType.TOKEN_EXPIRING_1_DAY.value == "TOKEN_EXPIRING_1_DAY"

    def test_notification_type_members(self):
        """Test NotificationType enum members."""
        expected_members = {
            "TOKEN_DEACTIVATED",
            "CABINET_DEACTIVATED",
            "TOKEN_EXPIRING_14_DAYS",
            "TOKEN_EXPIRING_3_DAYS",
            "TOKEN_EXPIRING_1_DAY",
        }

        actual_members = {member.name for member in NotificationType}
        assert actual_members == expected_members

    def test_notification_type_uniqueness(self):
        """Test that all NotificationType values are unique."""
        values = [member.value for member in NotificationType]
        assert len(values) == len(set(values))  # All values should be unique
