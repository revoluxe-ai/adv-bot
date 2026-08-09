"""Уведомление пользователя о empty-keywords pause (debounce + SUPPORT_LINK).

Spec: ``User notification on empty-keywords pause``.

PG: PURE_READ cabinets lookup через injectable ``session_maker`` /
``load_telegram_chat_ids_for_shop`` (parent→child session handoff).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.notification_sender import (
    NotificationSender,
    get_notification_sender,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.intent import (
    EmptyKeywordsPauseIntentManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.messages import (
    build_empty_keywords_pause_message,
)
from app.modules.token_monitoring.services.notification_manager import (
    get_wb_user_cabinets_for_shop,
)
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)

SessionMaker = Callable[..., AbstractAsyncContextManager[AsyncSession]]


async def load_telegram_chat_ids_for_shop(
    session: AsyncSession,
    shop_id: str,
) -> set[int]:
    """PURE_READ: telegram chat_id пользователей кабинетов магазина.

    Args:
        session: уже открытая PG session (parent handoff).
        shop_id: идентификатор WB-магазина.

    Returns:
        Множество ``user_telegram_id``; пустое, если кабинетов/tg нет.
    """
    cabinets = await get_wb_user_cabinets_for_shop(session, shop_id)
    chat_ids: set[int] = set()
    for uc in cabinets:
        user = getattr(uc, "user", None)
        tg = getattr(user, "user_telegram_id", None) if user is not None else None
        if tg is not None:
            chat_ids.add(int(tg))
    return chat_ids


async def notify_empty_keywords_pause(
    *,
    shop_id: str,
    adv_id: int,
    campaign_name: str,
    notification_sender: NotificationSender | None = None,
    intent_manager: EmptyKeywordsPauseIntentManager | None = None,
    session_maker: SessionMaker | None = None,
) -> None:
    """Once-per-enter notify: причина паузы + периодическая перепроверка.

    Debounce через Redis NX занимает слот на время попытки доставки.
    Если доставка не подтверждена (пустой ``shop_id``, нет chat_ids, все
    ``send_message`` False или unexpected error) — ключ снимается
    (`release_notified`), чтобы повтор в том же 24h окне мог доставить.
    Успех хотя бы в один чат оставляет debounce (once-per-enter).

    Ошибки доставки не пробрасываются наружу — pause уже применён.

    PG session: parent открывает ``session_maker(read_only=True)`` и передаёт
    session в ``load_telegram_chat_ids_for_shop`` (PURE_READ).
    """
    mgr = intent_manager or EmptyKeywordsPauseIntentManager()
    if not await mgr.mark_notified(adv_id):
        return

    text = build_empty_keywords_pause_message(
        campaign_name=campaign_name,
        adv_id=adv_id,
        include_support_link=True,
    )
    sender = notification_sender or get_notification_sender()
    delivered = False
    try:
        if not shop_id:
            logger.warning(
                "[adv_id=%s] empty-keywords notify skipped: empty shop_id",
                adv_id,
            )
            return
        sm: SessionMaker = session_maker or get_async_session_maker
        async with sm(read_only=True) as session:
            chat_ids = await load_telegram_chat_ids_for_shop(session, shop_id)
        if not chat_ids:
            logger.warning(
                "[adv_id=%s] empty-keywords notify: no telegram users shop_id=%s",
                adv_id,
                shop_id,
            )
            return
        for chat_id in chat_ids:
            ok = await sender.send_message(
                chat_id,
                text,
                disable_web_page_preview=True,
            )
            if ok:
                delivered = True
            else:
                logger.error(
                    "[adv_id=%s] empty-keywords notify failed chat_id=%s",
                    adv_id,
                    chat_id,
                )
    except Exception:
        logger.exception(
            "[adv_id=%s] empty-keywords notify unexpected error",
            adv_id,
        )
    finally:
        if not delivered:
            await mgr.release_notified(adv_id)
