# mypy ignore-errors

"""Token expiration monitoring service for proactive expiration notifications."""


import datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import WBToken
from app.modules.token_monitoring.models import (
    NotificationType,
    TokenNotificationTracker,
)
from app.modules.token_monitoring.services.notification_manager import (
    NotificationManager,
)
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)


class TokenExpirationService:
    """Service for monitoring token expiration dates and sending proactive notifications."""

    # Warning stages: days before expiry when to send notifications
    WARNING_STAGES = [14, 3, 1]

    # Map days to notification types
    DAYS_TO_NOTIFICATION_TYPE = {
        14: NotificationType.TOKEN_EXPIRING_14_DAYS.value,
        3: NotificationType.TOKEN_EXPIRING_3_DAYS.value,
        1: NotificationType.TOKEN_EXPIRING_1_DAY.value,
    }

    def __init__(
        self, notification_manager: NotificationManager = None, session_maker=None
    ):
        """
        Initialize the token expiration service.

        Args:
            notification_manager: Optional notification manager instance
            session_maker: Optional session maker
        """
        self.notification_manager = notification_manager or NotificationManager()
        self.session_maker = session_maker or get_async_session_maker

    async def check_token_expiration(self) -> dict[str, Any]:
        """
        Check all tokens for expiration and send appropriate notifications.

        This method should be called by a scheduled task (e.g., daily cron job).

        Returns:
            Dictionary with statistics about the expiration check
        """
        logger.info("Starting token expiration check")

        stats = {
            "total_tokens_checked": 0,
            "expiring_tokens_found": 0,
            "notifications_sent": 0,
            "notifications_skipped": 0,
            "errors": 0,
            "warnings_by_stage": {14: 0, 3: 0, 1: 0},
        }

        try:
            async with self.session_maker() as session:
                # Get all active tokens with expiration dates
                active_tokens = await self._get_active_tokens_with_expiry(session)
                stats["total_tokens_checked"] = len(active_tokens)

                logger.info(
                    f"Checking {len(active_tokens)} active tokens for expiration"
                )

                # Check each token for expiration warnings
                for token in active_tokens:
                    try:
                        await self._check_single_token_expiration(session, token, stats)
                    except Exception as e:
                        logger.error(
                            f"Error checking token {token.id}: {e}", exc_info=True
                        )
                        stats["errors"] += 1

                logger.info(f"Token expiration check completed: {stats}")
                return stats

        except Exception as e:
            logger.error(f"Failed to check token expiration: {e}", exc_info=True)
            stats["errors"] += 1
            return stats

    async def _check_single_token_expiration(
        self, session: AsyncSession, token: WBToken, stats: dict[str, Any]
    ) -> None:
        """
        Check a single token for expiration and send notifications if needed.

        Args:
            session: Database session
            token: Token to check
            stats: Statistics dictionary to update
        """
        if not token.shop_id:
            logger.debug(f"Token {token.id} has no shop_id, skipping")
            return

        # Calculate days until expiry
        now = datetime.datetime.now()
        if token.expires <= now:
            logger.debug(f"Token {token.id} already expired, skipping")
            return

        days_until_expiry = (token.expires - now).days

        # Check if this is a warning stage
        if days_until_expiry not in self.WARNING_STAGES:
            return

        stats["expiring_tokens_found"] += 1
        logger.debug(
            f"Token {token.id} for shop {token.shop_id} expires in {days_until_expiry} days"
        )

        # Check if notification already sent for this stage
        notification_type = self.DAYS_TO_NOTIFICATION_TYPE[days_until_expiry]
        already_notified = await self._notification_already_sent(
            session, token.shop_id, notification_type
        )

        if already_notified:
            logger.debug(
                f"Notification already sent for shop {token.shop_id}, "
                f"type {notification_type}"
            )
            stats["notifications_skipped"] += 1
            return

        # Send expiration warning
        try:
            await self.notification_manager.notify_token_issue(
                shop_id=token.shop_id,
                notification_type=notification_type,
                expiry_date=token.expires,
            )

            stats["notifications_sent"] += 1
            stats["warnings_by_stage"][days_until_expiry] += 1

            logger.info(
                f"Sent {days_until_expiry}-day expiration warning for shop {token.shop_id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to send expiration warning for shop {token.shop_id}: {e}",
                exc_info=True,
            )
            stats["errors"] += 1

    async def _get_active_tokens_with_expiry(
        self, session: AsyncSession
    ) -> list[WBToken]:
        """Get all active tokens that have expiration dates."""
        now = datetime.datetime.now()
        max_check_ahead = datetime.timedelta(days=max(self.WARNING_STAGES))
        cutoff_date = now + max_check_ahead

        stmt = (
            select(WBToken)
            .where(WBToken.active == True)  # noqa: E712 (SQLAlchemy requires == True)
            .where(WBToken.expires > now)  # Not yet expired
            .where(WBToken.expires <= cutoff_date)  # Within warning window
            .where(WBToken.shop_id.is_not(None))  # Has shop_id
        )

        result = await session.execute(stmt)
        return result.scalars().all()

    async def _notification_already_sent(
        self, session: AsyncSession, shop_id: str, notification_type: str
    ) -> bool:
        """Check if notification has already been sent for this shop and type."""
        stmt = (
            select(TokenNotificationTracker.id)
            .where(TokenNotificationTracker.shop_id == shop_id)
            .where(TokenNotificationTracker.notification_type == notification_type)
            .where(TokenNotificationTracker.resolved_at.is_(None))  # Not resolved
            .limit(1)
        )

        result = await session.execute(stmt)
        return result.scalar() is not None

    async def get_expiring_tokens_summary(self, days_ahead: int = 30) -> dict[str, Any]:
        """
        Get summary of tokens expiring within specified days.

        Args:
            days_ahead: Number of days to look ahead (default: 30)

        Returns:
            Dictionary with expiring tokens summary
        """
        async with self.session_maker() as session:
            now = datetime.datetime.now()
            cutoff_date = now + datetime.timedelta(days=days_ahead)

            stmt = (
                select(WBToken)
                .where(WBToken.active == True)  # noqa: E712
                .where(WBToken.expires > now)
                .where(WBToken.expires <= cutoff_date)
                .where(WBToken.shop_id.is_not(None))
            )

            result = await session.execute(stmt)
            expiring_tokens = result.scalars().all()

            # Group by shop and days until expiry
            summary = {
                "total_expiring": len(expiring_tokens),
                "by_shop": {},
                "by_days": {"1": [], "3": [], "7": [], "14": [], "30": []},
            }

            for token in expiring_tokens:
                days_until_expiry = (token.expires - now).days
                shop_id = token.shop_id

                # Add to shop summary
                if shop_id not in summary["by_shop"]:
                    summary["by_shop"][shop_id] = {  # type: ignore[index]
                        "tokens": [],
                        "earliest_expiry": token.expires,
                    }

                summary["by_shop"][shop_id]["tokens"].append(  # type: ignore[index]
                    {  # type: ignore[index]
                        "token_id": token.id,
                        "expires": token.expires,
                        "days_until_expiry": days_until_expiry,
                    }
                )

                if token.expires < summary["by_shop"][shop_id]["earliest_expiry"]:  # type: ignore[index]
                    summary["by_shop"][shop_id]["earliest_expiry"] = token.expires  # type: ignore[index]

                # Add to days summary
                if days_until_expiry <= 1:
                    summary["by_days"]["1"].append({"shop_id": shop_id, "token_id": token.id})  # type: ignore[index]
                elif days_until_expiry <= 3:
                    summary["by_days"]["3"].append({"shop_id": shop_id, "token_id": token.id})  # type: ignore[index]
                elif days_until_expiry <= 7:
                    summary["by_days"]["7"].append({"shop_id": shop_id, "token_id": token.id})  # type: ignore[index]
                elif days_until_expiry <= 14:
                    summary["by_days"]["14"].append({"shop_id": shop_id, "token_id": token.id})  # type: ignore[index]
                else:
                    summary["by_days"]["30"].append({"shop_id": shop_id, "token_id": token.id})  # type: ignore[index]

            return summary

    async def cleanup_resolved_notifications(self, older_than_days: int = 30) -> int:
        """
        Clean up old resolved notifications.

        Args:
            older_than_days: Remove resolved notifications older than this many days

        Returns:
            Number of notifications cleaned up
        """
        async with self.session_maker(read_only=False) as session:
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(
                days=older_than_days
            )

            # Find old resolved notifications
            stmt = (
                select(TokenNotificationTracker)
                .where(TokenNotificationTracker.resolved_at.is_not(None))
                .where(TokenNotificationTracker.resolved_at < cutoff_date)
            )

            result = await session.execute(stmt)
            old_notifications = result.scalars().all()

            # Delete them
            for notification in old_notifications:
                await session.delete(notification)

            await session.commit()

            logger.info(
                f"Cleaned up {len(old_notifications)} old resolved notifications"
            )
            return len(old_notifications)


# Convenience functions for external use
async def run_token_expiration_check() -> dict[str, Any]:
    """Run token expiration check."""
    service = TokenExpirationService()
    return await service.check_token_expiration()


async def get_expiring_tokens_summary(days_ahead: int = 30) -> dict[str, Any]:
    """Get summary of expiring tokens."""
    service = TokenExpirationService()
    return await service.get_expiring_tokens_summary(days_ahead)


async def cleanup_old_notifications(older_than_days: int = 30) -> int:
    """Clean up old resolved notifications."""
    service = TokenExpirationService()
    return await service.cleanup_resolved_notifications(older_than_days)
