"""Paid notify при enter shelf-exhausted pause (fanout shop-linked).

Spec: ``auto-shelf-exhausted-pause`` Notify. Pattern как empty-keywords,
без redesign биллинга.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.notification_sender import (
    NotificationSender,
    get_notification_sender,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.decision import (
    ResolveCpoKind,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.messages import (
    RESET_PAUSE_BUTTON_TEXT,
    build_shelf_exhausted_pause_message,
    build_shelf_exhausted_reset_callback_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.notify import (
    load_telegram_chat_ids_for_shop,
)
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)

SessionMaker = Callable[..., AbstractAsyncContextManager[AsyncSession]]


def build_reset_pause_keyboard(adv_setting_original_id: int) -> InlineKeyboardMarkup:
    """Inline-кнопка «Сбросить паузу» с callback_data ≤64 bytes."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=RESET_PAUSE_BUTTON_TEXT,
                    callback_data=build_shelf_exhausted_reset_callback_data(
                        adv_setting_original_id
                    ),
                )
            ]
        ]
    )


async def notify_shelf_exhausted_pause(
    *,
    shop_id: str,
    adv_id: int,
    shop_name: str,
    campaign_name: str,
    resolve_cpo_kind: ResolveCpoKind | str,
    resolve_cpo_value: float,
    due_at: datetime | None,
    adv_setting_original_id: int,
    notification_sender: NotificationSender | None = None,
    session_maker: SessionMaker | None = None,
) -> bool:
    """Отправить paid notify + кнопку; True если хотя бы один chat ok.

    Free guard: вызывающий MUST не вызывать для Free automation core.
    """
    if not shop_id:
        logger.warning(
            "[adv_id=%s] shelf-exhausted notify skipped: empty shop_id",
            adv_id,
        )
        return False
    text = build_shelf_exhausted_pause_message(
        shop_name=shop_name,
        campaign_name=campaign_name,
        resolve_cpo_kind=resolve_cpo_kind,
        resolve_cpo_value=resolve_cpo_value,
        due_at=due_at,
    )
    keyboard = build_reset_pause_keyboard(adv_setting_original_id)
    sender = notification_sender or get_notification_sender()
    sm: SessionMaker = session_maker or get_async_session_maker
    async with sm(read_only=True) as session:
        chat_ids = await load_telegram_chat_ids_for_shop(session, shop_id)
    if not chat_ids:
        logger.warning(
            "[adv_id=%s] shelf-exhausted notify: no telegram users shop_id=%s",
            adv_id,
            shop_id,
        )
        return False
    delivered = False
    for chat_id in chat_ids:
        ok = await sender.send_message(
            chat_id,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard,
        )
        if ok:
            delivered = True
        else:
            logger.error(
                "[adv_id=%s] shelf-exhausted notify failed chat_id=%s",
                adv_id,
                chat_id,
            )
    return delivered
