"""Token monitoring models for tracking notifications and token status."""

import datetime
from enum import Enum

from sqlalchemy import BIGINT, DateTime, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db.base import BaseTable


class NotificationType(Enum):
    """Enumeration of token notification types."""

    TOKEN_DEACTIVATED = "TOKEN_DEACTIVATED"
    TOKEN_EXPIRING_14_DAYS = "TOKEN_EXPIRING_14_DAYS"
    TOKEN_EXPIRING_3_DAYS = "TOKEN_EXPIRING_3_DAYS"
    TOKEN_EXPIRING_1_DAY = "TOKEN_EXPIRING_1_DAY"


# Keep separate from NotificationType to preserve historical enum contract in tests.
CABINET_DEACTIVATED_NOTIFICATION_TYPE = "CABINET_DEACTIVATED"


class TokenNotificationTracker(BaseTable):
    """
    Table for tracking token-related notifications sent to users.

    Prevents duplicate notifications and provides audit trail for token issues.
    The unique constraint ensures only one notification per (shop_id, user_telegram_id, notification_type).
    """

    __tablename__ = "token_notification_tracker"

    # Shop identifier from WBCabinet
    shop_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Telegram user ID from User model
    user_telegram_id: Mapped[int] = mapped_column(BIGINT, nullable=False, index=True)

    # Type of notification sent
    notification_type: Mapped[str] = mapped_column(String, nullable=False)

    # Token expiration date (nullable for deactivation notifications)
    token_expiry_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    # When notification was sent
    sent_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()"), index=True
    )

    # When the token issue was resolved (nullable until resolved)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    __table_args__ = (
        # Unique constraint prevents duplicate notifications for same shop/user/type
        UniqueConstraint(
            "shop_id",
            "user_telegram_id",
            "notification_type",
            name="uq_token_notification_shop_user_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TokenNotificationTracker("
            f"shop_id='{self.shop_id}', "
            f"user_telegram_id={self.user_telegram_id}, "
            f"type='{self.notification_type}', "
            f"sent_at='{self.sent_at}'"
            f")>"
        )

    @property
    def is_resolved(self) -> bool:
        """Check if the token issue has been resolved."""
        return self.resolved_at is not None

    def mark_resolved(self) -> None:
        """Mark this notification as resolved."""
        self.resolved_at = datetime.datetime.utcnow()
