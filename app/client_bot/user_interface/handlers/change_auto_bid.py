"""Изменить ставку в автокампании с валидацией по минимальной ставке WB API."""

import logging

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.mp.wb.api.excs import ApiForbiddenError
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.auto_bid_freeze import (
    AB_HOLD_MANUAL_AUTO_BID_BLOCKED_MSG,
    is_ab_hold_auto_bid_manual_blocked,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

from .. import states
from ..views import callbacks
from ..views.messages.main_adv_setting_menu import AdvSettingMenu
from . import start

logger = logging.getLogger(__name__)

sm = get_async_session_maker
router = Router()


async def _get_wb_user_cabinet_for_adv_and_telegram(
    session, adv_setting: AdvSetting, telegram_id: int
) -> WBUserCabinet | None:
    """Найти WBUserCabinet текущего пользователя для кабинета кампании."""
    stmt = (
        select(WBUserCabinet)
        .join(User, User.id == WBUserCabinet.user_id)
        .where(User.user_telegram_id == telegram_id)
        .where(WBUserCabinet.wb_cabinet_id == adv_setting.wb_cabinet_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


@router.callback_query(
    callbacks.ChangeAutoBid.filter(F.action == "open"),
)
async def open_change_auto_bid(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChangeAutoBid,
    state: FSMContext,
):
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id
    telegram_id = callback.from_user.id if callback.from_user else 0
    adv_original_id = callback_data.adv_original_id

    async with sm() as session:
        stmt = (
            select(AdvSetting)
            .options(joinedload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == adv_original_id)
        )
        result = await session.execute(stmt)
        adv_setting = result.scalar_one_or_none()

    if not adv_setting:
        await callback.bot.send_message(chat_id, "Рекламная кампания не найдена.")
        return

    if is_ab_hold_auto_bid_manual_blocked(adv_setting.card_ab_hold_mode):
        await callback.bot.send_message(chat_id, AB_HOLD_MANUAL_AUTO_BID_BLOCKED_MSG)
        return

    if not adv_setting.adv_id:
        await callback.bot.send_message(
            chat_id,
            "Кампания не поддерживается: отсутствует авто-РК (adv_id).",
        )
        return

    nmids = list(adv_setting.nmids) if adv_setting.nmids else []
    if not nmids:
        await callback.bot.send_message(
            chat_id,
            "В кампании нет товаров (nmids). Невозможно получить минимальную ставку.",
        )
        return

    try:
        # Только авто: минимальные ставки и изменение ставки по adv_id (авто-кампания)
        complex_adv = ComplexAdv(adv_setting, None)
        shop_id = adv_setting.wb_cabinet.shop_id

        async with await DIManager.create(AppContainer) as container: # type: ignore
            factory = (
                container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
            )
            hub = factory.get_wb_manager_hub(shop_id)
            min_bids = await hub.wb_manager.get_min_bids_cache_only(
                [complex_adv],
                context="change_auto_bid",
            )
    except ApiForbiddenError:
        await callback.bot.send_message(
            chat_id,
            "Нет доступа к API WB. Проверьте токены магазина.",
        )
        return
    except Exception as e:
        logger.exception("Unexpected error getting min bids for adv_original_id=%s", adv_original_id)
        await callback.bot.send_message(
            chat_id,
            "Произошла ошибка при запросе минимальной ставки. Попробуйте позже.",
        )
        return

    missing_nmids = [nmid for nmid in nmids if nmid not in min_bids.auto]
    if missing_nmids:
        await callback.bot.send_message(
            chat_id,
            "Нет минимальных ставок в кеше для части товаров. Дождитесь обновления кеша.",
        )
        return
    effective_min = max(min_bids.auto[nmid] for nmid in nmids)
    if effective_min <= 0:
        await callback.bot.send_message(
            chat_id,
            "Не удалось определить минимальную ставку для кампании.",
        )
        return

    await state.update_data(
        adv_original_id=adv_original_id,
        effective_min=effective_min,
        auto_adv_id=adv_setting.adv_id,
        nmids=nmids,
    )
    await state.set_state(states.ChangeAutoBid.waiting_for_new_bid)

    text = (
        f"Минимальная ставка для этой автокампании: {effective_min} руб.\n"
        f"Введите новую ставку (целое число, не меньше {effective_min}):"
    )
    await callback.bot.send_message(chat_id, text)


@router.message(StateFilter(states.ChangeAutoBid.waiting_for_new_bid))
async def set_auto_bid(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    telegram_id = message.from_user.id if message.from_user else 0
    text = message.text

    if text and "/start" in text:
        await state.clear()
        await start.start_registration(message, message.bot, state)
        return

    try:
        new_cpm = int(text.strip()) if text else None
    except (ValueError, AttributeError):
        new_cpm = None

    if new_cpm is None:
        await message.bot.send_message(
            chat_id,
            "Введите целое число (ставку в рублях).",
        )
        return

    data = await state.get_data()
    effective_min = data.get("effective_min")
    adv_original_id = data.get("adv_original_id")
    auto_adv_id = data.get("auto_adv_id")
    nmids = data.get("nmids")

    if effective_min is None or adv_original_id is None or auto_adv_id is None or nmids is None:
        await message.bot.send_message(
            chat_id,
            "Сессия устарела. Вернитесь в меню кампании и нажмите «Изменить ставку в Авто» снова.",
        )
        await state.clear()
        return

    if new_cpm < effective_min:
        await message.bot.send_message(
            chat_id,
            f"Ставка не может быть меньше минимальной ({effective_min} руб).",
        )
        return

    async with sm() as session:
        result = await session.execute(
            select(AdvSetting).options(joinedload(AdvSetting.wb_cabinet)).where(
                AdvSetting.id == adv_original_id
            )
        )
        adv_setting = result.scalar_one_or_none()

    if not adv_setting:
        await message.bot.send_message(chat_id, "Рекламная кампания не найдена.")
        await state.clear()
        return

    if is_ab_hold_auto_bid_manual_blocked(adv_setting.card_ab_hold_mode):
        await message.bot.send_message(chat_id, AB_HOLD_MANUAL_AUTO_BID_BLOCKED_MSG)
        await state.clear()
        return

    shop_id = adv_setting.wb_cabinet.shop_id
    nm_bid_pairs = {nmid: new_cpm for nmid in nmids}

    try:
        async with await DIManager.create(AppContainer) as container: # type: ignore
            factory = (
                container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
            )
            hub = factory.get_wb_manager_hub(shop_id)
            await hub.wb_modifier.update_auto_adv_cpm(auto_adv_id, nm_bid_pairs)
    except ApiForbiddenError:
        await message.bot.send_message(
            chat_id,
            "Нет доступа к API WB. Проверьте токены магазина.",
        )
        return
    except Exception as e:
        logger.exception(
            "update_auto_adv_cpm failed for adv_id=%s: %s", auto_adv_id, e
        )
        await message.bot.send_message(
            chat_id,
            "Ошибка при обновлении ставки в WB. Попробуйте позже.",
        )
        return

    async with sm(read_only=False) as session:
        adv = await session.get(AdvSetting, adv_original_id)
        if adv:
            adv.cpm = new_cpm
            await session.commit()

    await state.clear()
    await message.bot.send_message(
        chat_id,
        f"Ставка в автокампании обновлена: {new_cpm} руб.",
    )

    async with sm() as session:
        result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv_for_menu = result.scalar_one_or_none()
        if not adv_for_menu:
            return
        wb_user_cabinet = await _get_wb_user_cabinet_for_adv_and_telegram(
            session, adv_for_menu, telegram_id
        )
        if wb_user_cabinet:
            await AdvSettingMenu(
                message.bot,
                chat_id,
                wb_user_cabinet,
                adv_for_menu,
            )()
