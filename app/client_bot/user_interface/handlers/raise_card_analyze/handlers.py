"""Handlers for Raise Card Analyze: menu, result, by_days, buckets, what_next."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.future import select

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dependency_injector.wiring import inject, Provide

from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.keyboards import get_return_to_adv_setting_keyboard
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker

from app.modules.raise_card_analyze import (
    RaiseCardAnalyzeClickHouseManager,
    RaiseCardAnalyzeCache,
    CampaignGrowthAnalysisService,
)
from app.modules.raise_card_analyze.constants import (
    SERIES_DAYS_COLD,
    SERIES_WEEKS_NORMAL,
    WINDOW_DAYS_FOR_K_COLD,
    WINDOW_DAYS_FOR_K_NORMAL,
    MIN_D_VIEWS_COLD,
    MIN_D_VIEWS_NORMAL,
)

from .messages import format_raise_card_result

logger = logging.getLogger(__name__)
router = Router()
_sm = get_async_session_maker


async def _get_adv_setting(adv_setting_id: int) -> AdvSetting | None:
    async with _sm() as session:
        result = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_setting_id))
        return result.scalar_one_or_none()


@router.callback_query(callbacks.RaiseCardAnalyze.filter())
@inject
async def raise_card_analyze_callback(
    callback: types.CallbackQuery,
    callback_data: callbacks.RaiseCardAnalyze,
    redis_client=Provide["redis_client_wrapper"],
) -> None:
    """Handle RaiseCardAnalyze: menu (choose nmid or run), result (with nmid)."""
    if not callback.message:
        return
    bot = callback.bot
    adv_setting_id = callback_data.adv_setting_original_id
    action = callback_data.action or "menu"
    nmid = callback_data.nmid

    adv = await _get_adv_setting(adv_setting_id)
    if not adv:
        await callback.message.answer("Кампания не найдена.")
        return

    nmids = adv.nmids or []
    if not nmids:
        await callback.message.answer(
            "В кампании нет товаров (nmids). Добавьте товар в настройках.",
            reply_markup=get_return_to_adv_setting_keyboard(adv_setting_id),
        )
        return

    if action == "menu":
        if len(nmids) == 1:
            # Run analysis immediately for single product
            await _run_analysis_and_reply(
                bot, callback.message, adv, nmids[0], redis_client
            )
        else:
            # Show product choice
            rows = [
                [InlineKeyboardButton(
                    text=f"Товар {nid}",
                    callback_data=callbacks.RaiseCardAnalyze(
                        adv_setting_original_id=adv_setting_id,
                        action="result",
                        nmid=nid,
                    ).pack(),
                )]
                for nid in nmids
            ]
            rows.append([
                InlineKeyboardButton(
                    text="Назад в настройки кампании",
                    callback_data=callbacks.Adv(adv_original_id=adv_setting_id).pack(),
                )
            ])
            await callback.message.answer(
                "Выберите товар для анализа раскрутки:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            )
        return

    if action == "result" and nmid is not None:
        await _run_analysis_and_reply(
            bot, callback.message, adv, nmid, redis_client
        )
        return

    if action == "by_days" and nmid is not None:
        await _show_view(bot, callback.message, adv, nmid, redis_client, "by_days")
        return

    if action == "by_weeks" and nmid is not None:
        await _show_view(bot, callback.message, adv, nmid, redis_client, "by_weeks")
        return

    await callback.message.answer(
        "Используйте «Назад в настройки кампании».",
        reply_markup=get_return_to_adv_setting_keyboard(adv_setting_id),
    )


async def _run_analysis_and_reply(
    bot: types.Bot,
    message: types.Message,
    adv: AdvSetting,
    nmid: int,
    redis_client: Any,
) -> None:
    """Send 'Считаю…', then run analysis (or get cache), format and edit."""
    progress_msg = await message.answer("Считаю…")
    chat_id = message.chat.id
    adv_id = adv.search_adv_id or adv.adv_id
    try:
        payload = await _get_payload(adv_id, nmid, redis_client, is_cold=True)
    except Exception:
        logger.exception("Raise card analyze failed")
        raise
    if not payload:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=progress_msg.message_id,
            text="Нет данных.",
            reply_markup=get_return_to_adv_setting_keyboard(adv.id),
        )
        return
    if message.from_user is None:
        return
    user_id = message.from_user.id
    text = format_raise_card_result(payload, adv.id, view="by_days", user_id=user_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Анализ по неделям", callback_data=callbacks.RaiseCardAnalyze(
            adv_setting_original_id=adv.id, action="by_weeks", nmid=nmid).pack())],
        [InlineKeyboardButton(
            text="Назад в настройки кампании",
            callback_data=callbacks.Adv(adv_original_id=adv.id).pack(),
        )],
    ])
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=progress_msg.message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


async def _get_payload(
    adv_id: int,
    nmid: int,
    redis_client: Any,
    is_cold: bool,
) -> dict[str, Any] | None:
    """Get analysis payload from cache or run service. Returns None on error."""
    ch_manager = RaiseCardAnalyzeClickHouseManager()
    service = CampaignGrowthAnalysisService(ch_manager)
    cache = RaiseCardAnalyzeCache(redis_client)
    calc_profile = "cold" if is_cold else "normal"
    trend_mode = "7v7" if is_cold else "wow"
    window_days = WINDOW_DAYS_FOR_K_COLD if is_cold else WINDOW_DAYS_FOR_K_NORMAL
    series_days = SERIES_DAYS_COLD if is_cold else (SERIES_WEEKS_NORMAL * 7)
    min_d = MIN_D_VIEWS_COLD if is_cold else MIN_D_VIEWS_NORMAL
    for k_src in ("item", "adv", "category", "global"):
        cached = await cache.get(
            adv_id, nmid, calc_profile, k_src, window_days, series_days, min_d, trend_mode
        )
        if cached:
            return cached
    payload = await service.run_full_analysis(adv_id, nmid, is_cold=is_cold)
    await cache.set(
        adv_id, nmid, calc_profile, payload["k_result"].k_source,
        window_days, series_days, min_d, trend_mode, payload,
    )
    return payload


async def _show_view(
    bot: types.Bot,
    message: types.Message,
    adv: AdvSetting,
    nmid: int,
    redis_client: Any,
    view: str,
) -> None:
    """Edit message to 'Загружаю…', get payload, then show view (by_days | by_weeks)."""
    chat_id = message.chat.id
    adv_id = adv.search_adv_id or adv.adv_id
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text="Загружаю…",
        )
    except Exception:
        pass
    try:
        is_cold = view == "by_days"
        payload = await _get_payload(adv_id, nmid, redis_client, is_cold=is_cold)
    except Exception:
        logger.exception("Raise card analyze view failed")
        raise
    if not payload:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text="Нет данных.",
            reply_markup=get_return_to_adv_setting_keyboard(adv.id),
        )
        return
    user_id = message.from_user.id if message.from_user else message.chat.id
    text = format_raise_card_result(payload, adv.id, view=view, user_id=user_id)
    if view == "by_days":
        toggle_btn = InlineKeyboardButton(
            text="Анализ по неделям",
            callback_data=callbacks.RaiseCardAnalyze(
                adv_setting_original_id=adv.id, action="by_weeks", nmid=nmid
            ).pack(),
        )
    else:
        toggle_btn = InlineKeyboardButton(
            text="Анализ по дням",
            callback_data=callbacks.RaiseCardAnalyze(
                adv_setting_original_id=adv.id, action="by_days", nmid=nmid
            ).pack(),
        )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [toggle_btn],
        [InlineKeyboardButton(
            text="Назад в настройки кампании",
            callback_data=callbacks.Adv(adv_original_id=adv.id).pack(),
        )],
    ])
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message.message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )
