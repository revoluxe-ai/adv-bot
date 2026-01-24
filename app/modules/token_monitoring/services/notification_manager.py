"""Notification manager for sending token-related alerts to users."""

import datetime
import logging
from typing import Any, Callable

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import WBUserCabinet

from app.client_bot.notification_sender import (
    NotificationSender,
    get_notification_sender,
)
from app.modules.token_monitoring.models import (
    NotificationType,
    TokenNotificationTracker,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)

# TODO: Сделать уникальность токенов на уровне пользователя, сейчас проверка при только при добавлении в базу


class NotificationManager:
    """Manager for sending token-related notifications to users."""

    # Message templates for different notification types
    MESSAGE_TEMPLATES = {
        NotificationType.TOKEN_DEACTIVATED.value: (
            "Токен истек или деактивирован, сделайте срочно новый и добавьте в магазин {shop_name}"
        ),
        NotificationType.TOKEN_EXPIRING_14_DAYS.value: (
            "Токен для магазина {shop_name} истекает через 2 недели ({expiry_date}). "
            "Подготовьте новый токен заранее"
        ),
        NotificationType.TOKEN_EXPIRING_3_DAYS.value: (
            "Внимание! Токен для магазина {shop_name} истекает через 3 дня ({expiry_date}). "
            "Срочно подготовьте новый токен"
        ),
        NotificationType.TOKEN_EXPIRING_1_DAY.value: (
            "СРОЧНО! Токен для магазина {shop_name} истекает завтра ({expiry_date}). "
            "Добавьте новый токен сегодня"
        ),
    }

    def __init__(
        self,
        bot: Bot | None = None,
        notification_sender: NotificationSender | None = None,
        session_maker: Callable[..., AsyncSession] | None = None,
    ) -> None:
        """
        Initialize the notification manager.

        Args:
            bot: Optional Bot instance. If provided, its token is used to build a sender.
            notification_sender: Optional notification sender.
            session_maker: Optional session maker. If None, uses default.
        """
        self.session_maker = session_maker or get_async_session_maker
        if notification_sender is not None:
            self._notification_sender = notification_sender
        elif bot is not None:
            token = bot.token
            self._notification_sender = NotificationSender([token])
        else:
            self._notification_sender = get_notification_sender()

    @staticmethod
    def _to_naive_utc(dt: datetime.datetime | None) -> datetime.datetime | None:
        """
        Convert a datetime to a timezone-naive UTC value.

        This ensures compliance with TIMESTAMP WITHOUT TIME ZONE columns.
        """
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(datetime.UTC).replace(tzinfo=None)

    async def notify_token_issue(
        self,
        shop_id: str,
        notification_type: str,
        expiry_date: datetime.datetime | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Send token issue notification to all users of a shop.

        Args:
            shop_id: The shop ID where token issue occurred
            notification_type: Type of notification (from NotificationType enum)
            expiry_date: Token expiration date (for expiration notifications)
            context: Additional context information
        """
        try:
            async with self.session_maker(read_only=False) as session:
                # Get all users for this shop
                shop_users = await self._get_shop_users(session, shop_id)

                if not shop_users:
                    logger.warning("No users found for shop %s", shop_id)
                    return

                # Get shop name from first user cabinet
                shop_name = shop_users[0].name if shop_users else f"Магазин {shop_id}"

                # Format message based on notification type
                message = self._format_message(
                    notification_type, shop_name, expiry_date
                )

                # Send notifications to all users
                notifications_sent = 0
                for user_cabinet in shop_users:
                    success = await self._send_notification_to_user(
                        session=session,
                        shop_id=shop_id,
                        user_cabinet=user_cabinet,
                        notification_type=notification_type,
                        message=message,
                        expiry_date=expiry_date,
                    )
                    if success:
                        notifications_sent += 1

                await session.commit()

                logger.info(
                    "Sent %s notifications for shop %s, type: %s",
                    notifications_sent,
                    shop_id,
                    notification_type,
                )

        except Exception as e:
            logger.error(
                "Failed to send notifications for shop %s, type %s: %s",
                shop_id,
                notification_type,
                e,
                exc_info=True,
            )

    async def _send_notification_to_user(
        self,
        session: AsyncSession,
        shop_id: str,
        user_cabinet: WBUserCabinet,
        notification_type: str,
        message: str,
        expiry_date: datetime.datetime | None = None,
    ) -> bool:
        """
        Send notification to a single user and record it in database.

        Args:
            session: Database session
            shop_id: Shop ID
            user_cabinet: User cabinet object
            notification_type: Type of notification
            message: Formatted message to send
            expiry_date: Token expiration date

        Returns:
            True if notification was sent successfully, False otherwise
        """
        user_telegram_id = user_cabinet.user.user_telegram_id
        try:
            sent = await self._notification_sender.send_message(
                user_telegram_id,
                message,
                disable_web_page_preview=True,
            )
            if not sent:
                logger.warning(
                    "Notification sender failed for user %s, shop %s",
                    user_telegram_id,
                    shop_id,
                )
                return False

            notification = TokenNotificationTracker(
                shop_id=shop_id,
                user_telegram_id=user_telegram_id,
                notification_type=notification_type,
                token_expiry_date=self._to_naive_utc(expiry_date),
                sent_at=self._to_naive_utc(datetime.datetime.now(datetime.UTC)),
            )

            session.add(notification)
            await session.flush()  # Flush to check for constraint violations

            logger.debug(
                "Notification sent to user %s for shop %s",
                user_telegram_id,
                shop_id,
            )
            return True

        except IntegrityError:
            logger.debug(
                "Duplicate notification prevented for user %s, shop %s, type %s",
                user_telegram_id,
                shop_id,
                notification_type,
            )
            await session.rollback()
            return False

        except Exception as e:
            logger.error(
                "Failed to send notification to user %s for shop %s: %s",
                user_telegram_id,
                shop_id,
                e,
                exc_info=True,
            )
            return False

    async def _get_shop_users(
        self, session: AsyncSession, shop_id: str
    ) -> list[WBUserCabinet]:
        """Get all user cabinets for a shop."""
        stmt = (
            select(WBUserCabinet)
            .options(selectinload(WBUserCabinet.user))
            .join(WBCabinet)
            .join(User)
            .where(WBCabinet.shop_id == shop_id)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def _format_message(
        self,
        notification_type: str,
        shop_name: str,
        expiry_date: datetime.datetime | None = None,
    ) -> str:
        """
        Format notification message based on type and parameters.

        Args:
            notification_type: Type of notification
            shop_name: Name of the shop
            expiry_date: Token expiration date (for expiration notifications)

        Returns:
            Formatted message string
        """
        template = self.MESSAGE_TEMPLATES.get(notification_type)
        if not template:
            logger.warning(
                "No template found for notification type: %s", notification_type
            )
            return f"Проблема с токеном для магазина {shop_name}"

        # Format expiry date if provided
        expiry_date_str = ""
        if expiry_date:
            expiry_date_str = expiry_date.strftime("%d.%m.%Y")

        # Format message with available parameters
        try:
            message = template.format(shop_name=shop_name, expiry_date=expiry_date_str)
        except KeyError as e:
            logger.warning(
                "Template formatting error for %s: %s", notification_type, e
            )
            message = f"Проблема с токеном для магазина {shop_name}"

        return message

    async def mark_notifications_resolved(
        self, shop_id: str, notification_type: str
    ) -> int:
        """
        Mark notifications as resolved for a shop and notification type.

        Args:
            shop_id: Shop ID
            notification_type: Type of notification to resolve

        Returns:
            Number of notifications marked as resolved
        """
        async with self.session_maker(read_only=False) as session:
            # Find unresolved notifications
            stmt = (
                select(TokenNotificationTracker)
                .where(TokenNotificationTracker.shop_id == shop_id)
                .where(TokenNotificationTracker.notification_type == notification_type)
                .where(TokenNotificationTracker.resolved_at.is_(None))
            )

            result = await session.execute(stmt)
            notifications = result.scalars().all()

            # Mark as resolved
            resolved_count = 0
            for notification in notifications:
                notification.mark_resolved()
                resolved_count += 1

            await session.commit()

            logger.debug(
                "Marked %s notifications as resolved for shop %s, type: %s",
                resolved_count,
                shop_id,
                notification_type,
            )

            return resolved_count

    async def get_notification_history(
        self, shop_id: str, limit: int = 100
    ) -> list[TokenNotificationTracker]:
        """
        Get notification history for a shop.

        Args:
            shop_id: Shop ID
            limit: Maximum number of records to return

        Returns:
            List of notification records
        """
        async with self.session_maker() as session:
            stmt = (
                select(TokenNotificationTracker)
                .where(TokenNotificationTracker.shop_id == shop_id)
                .order_by(TokenNotificationTracker.sent_at.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
        if not result:
            return []

        return list(result.scalars().all())


# Convenience functions
async def notify_token_deactivation(
    shop_id: str, context: dict[str, Any] | None = None
) -> None:
    """Send token deactivation notification."""
    manager = NotificationManager()
    await manager.notify_token_issue(
        shop_id=shop_id,
        notification_type=NotificationType.TOKEN_DEACTIVATED.value,
        context=context,
    )


async def notify_token_expiring(
    shop_id: str, days_until_expiry: int, expiry_date: datetime.datetime
) -> None:
    """Send token expiration notification based on days until expiry."""
    # Determine notification type based on days until expiry
    if days_until_expiry == 14:
        notification_type = NotificationType.TOKEN_EXPIRING_14_DAYS.value
    elif days_until_expiry == 3:
        notification_type = NotificationType.TOKEN_EXPIRING_3_DAYS.value
    elif days_until_expiry == 1:
        notification_type = NotificationType.TOKEN_EXPIRING_1_DAY.value
    else:
        logger.warning(f"Unsupported expiry notification for {days_until_expiry} days")
        return

    manager = NotificationManager()
    await manager.notify_token_issue(
        shop_id=shop_id, notification_type=notification_type, expiry_date=expiry_date
    )
