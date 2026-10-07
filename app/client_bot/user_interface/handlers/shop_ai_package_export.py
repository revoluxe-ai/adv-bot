"""Telegram-транспорт Full AI Package для меню магазина.

Поток: callback ``WBUserCabinet.id`` → владелец → ``WBCabinet.shop_id`` →
``PackageZipAssembler.assemble_zip`` → ``send_document``. Запись в WB, PG
настроек и ClickHouse отсюда недостижима.
"""

from __future__ import annotations

import logging

import aiogram
from aiogram import Router
from aiogram.types import BufferedInputFile, CallbackQuery

from app.client_bot.user_interface.services.adv_excel_roundtrip.import_apply import (
    verify_user_owns_wb_user_cabinet,
)
from app.client_bot.user_interface.services.shop_ai_package_export.flow import (
    ACCESS_DENIED_TEXT,
    ALREADY_RUNNING_TEXT,
    EXPORT_FAILED_TEXT,
    FORMING_TEXT,
    SHOP_UNRESOLVED_TEXT,
    SIZE_REJECTED_TEXT,
    assemble_shop_package,
    build_ai_package_caption,
    build_ai_package_filename,
    inflight_guard,
    is_telegram_file_too_large,
    resolve_canonical_shop_id,
    v1_shop_menu_export_period,
)
from app.client_bot.user_interface.views import callbacks

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(callbacks.ExportShopAiPackage.filter())
async def export_shop_ai_package(
    callback: CallbackQuery,
    callback_data: callbacks.ExportShopAiPackage,
    bot: aiogram.Bot,
) -> None:
    """Собрать AI-пакет на сервере WB Sky и отправить ZIP в чат.

    ACK callback уже делает middleware. Перед долгой сборкой отправляется
    «Формирую AI-пакет…». Повторный клик того же пользователя по тому же
    кабинету не запускает второй assembler.

    Args:
        callback: Входящий callback магазина.
        callback_data: Только ``wb_user_cabinet_original_id``.
        bot: Бот для ``send_message`` / ``send_document``.
    """
    if callback.message is None:
        return
    from_user = callback.from_user
    chat_id = callback.message.chat.id
    wb_uc_id = callback_data.wb_user_cabinet_original_id
    try:
        _ = await verify_user_owns_wb_user_cabinet(
            telegram_user_id=from_user.id,
            wb_user_cabinet_id=wb_uc_id,
        )
    except PermissionError:
        logger.info(
            "ai package export denied telegram_user_id=%s wb_user_cabinet_id=%s",
            from_user.id,
            wb_uc_id,
        )
        _ = await bot.send_message(chat_id, ACCESS_DENIED_TEXT)
        return

    lock = await inflight_guard().try_acquire(from_user.id, wb_uc_id)
    if lock is None:
        _ = await bot.send_message(chat_id, ALREADY_RUNNING_TEXT)
        return

    shop_id: str | None = None
    try:
        _ = await bot.send_message(chat_id, FORMING_TEXT)
        shop_id = await resolve_canonical_shop_id(wb_uc_id)
        if shop_id is None:
            logger.warning(
                "ai package shop mapping failed telegram_user_id=%s "
                "wb_user_cabinet_id=%s",
                from_user.id,
                wb_uc_id,
            )
            _ = await bot.send_message(chat_id, SHOP_UNRESOLVED_TEXT)
            return

        period = v1_shop_menu_export_period()
        try:
            zip_bytes = await assemble_shop_package(shop_id, period)
        except Exception:
            logger.exception(
                "ai package export failed telegram_user_id=%s "
                "wb_user_cabinet_id=%s shop_id=%s",
                from_user.id,
                wb_uc_id,
                shop_id,
            )
            _ = await bot.send_message(chat_id, EXPORT_FAILED_TEXT)
            return

        filename = build_ai_package_filename(shop_id, period)
        caption = build_ai_package_caption(shop_id, period)
        try:
            _ = await bot.send_document(
                chat_id=chat_id,
                document=BufferedInputFile(zip_bytes, filename),
                caption=caption,
            )
        except Exception as exc:
            if is_telegram_file_too_large(exc):
                logger.warning(
                    "ai package telegram size reject telegram_user_id=%s "
                    "wb_user_cabinet_id=%s shop_id=%s",
                    from_user.id,
                    wb_uc_id,
                    shop_id,
                )
                _ = await bot.send_message(chat_id, SIZE_REJECTED_TEXT)
                return
            logger.exception(
                "ai package telegram send failed telegram_user_id=%s "
                "wb_user_cabinet_id=%s shop_id=%s",
                from_user.id,
                wb_uc_id,
                shop_id,
            )
            _ = await bot.send_message(chat_id, EXPORT_FAILED_TEXT)
    finally:
        lock.release()
