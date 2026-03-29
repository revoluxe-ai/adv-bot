"""WBCabinet active flag updates with user notification tracking in one DB transaction."""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.client_bot.notification_sender import get_notification_sender
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.token_monitoring.models import TokenNotificationTracker
from app.modules.token_monitoring.services.notification_manager import (
    NotificationManager,
    get_wb_user_cabinets_for_shop,
)
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)

sm = get_async_session_maker


async def deactivate_cabinet_atomic_with_user_trackers(
    shop_id: str,
    *,
    notification_type: str,
) -> bool:
    """
    Set WBCabinet.active=False and insert TokenNotificationTracker rows in one commit.

    Sends Telegram only to users who received a new tracker row (best-effort I/O after commit).

    Returns False if no WBCabinet row exists for shop_id.
    """
    notification_manager = NotificationManager()
    inserted_telegram_ids: list[int] = []

    async with sm(read_only=False) as session:
        stmt = select(WBCabinet).where(WBCabinet.shop_id == shop_id)
        result = await session.execute(stmt)
        cabinet = result.scalar_one_or_none()
        if cabinet is None:
            return False

        if cabinet.active is False:
            return True

        cabinet.active = False

        shop_users = await get_wb_user_cabinets_for_shop(session, shop_id)
        shop_name = shop_users[0].name if shop_users else f"Магазин {shop_id}"
        now_naive = NotificationManager.naive_utc_now()

        for uc in shop_users:
            uid = uc.user.user_telegram_id
            existing = await session.execute(
                select(TokenNotificationTracker.id)
                .where(
                    TokenNotificationTracker.shop_id == shop_id,
                    TokenNotificationTracker.user_telegram_id == uid,
                    TokenNotificationTracker.notification_type == notification_type,
                )
                .limit(1)
            )
            if existing.scalar_one_or_none() is not None:
                continue
            session.add(
                TokenNotificationTracker(
                    shop_id=shop_id,
                    user_telegram_id=uid,
                    notification_type=notification_type,
                    token_expiry_date=None,
                    sent_at=now_naive,
                )
            )
            inserted_telegram_ids.append(uid)

        await session.commit()

    message = notification_manager.format_shop_notification_message(
        notification_type, shop_name, expiry_date=None
    )
    sender = get_notification_sender()
    for uid in inserted_telegram_ids:
        try:
            sent = await sender.send_message(
                uid,
                message,
                disable_web_page_preview=True,
            )
            if not sent:
                logger.warning(
                    "Cabinet deactivate: telegram send failed user=%s shop=%s",
                    uid,
                    shop_id,
                )
        except Exception:
            logger.exception(
                "Cabinet deactivate: telegram error user=%s shop=%s",
                uid,
                shop_id,
            )

    return True


async def activate_cabinet(shop_id: str) -> bool:
    """Set WBCabinet.active=True. Returns False if cabinet not found."""
    async with sm(read_only=False) as session:
        stmt = select(WBCabinet).where(WBCabinet.shop_id == shop_id)
        result = await session.execute(stmt)
        cabinet = result.scalar_one_or_none()
        if cabinet is None:
            return False
        cabinet.active = True
        await session.commit()
    return True
