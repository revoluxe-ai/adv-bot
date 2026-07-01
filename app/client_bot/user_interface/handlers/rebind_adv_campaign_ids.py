"""Ручная перепривязка кампаний WB: колонка adv_id (авто) и _search_adv_id (поиск/аукцион).

Пользовательским текстам не показываем имена полей — только смысл (ручная/единая ставка).
"""

from __future__ import annotations

import logging
from typing import Literal

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.common_slaves.wildberries.rebind_wb_adv_ids_history import (
    append_rebound_wb_adv_id,
)
from app.modules.common_slaves.wildberries.search_adv_settings import (
    ensure_search_adv_setting_for_main_adv,
)
from app.modules.connect_existing_advs.candidates_service import (
    classify_wb_campaign_for_rebind,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

from .. import states
from ..views import callbacks
from ..views.messages.main_adv_setting_menu import AdvSettingMenu
from . import start

logger = logging.getLogger(__name__)

router = Router()


async def _get_wb_user_cabinet_for_adv_and_telegram(
    session, adv_setting: AdvSetting, telegram_id: int
) -> WBUserCabinet | None:
    stmt = (
        select(WBUserCabinet)
        .join(User, User.id == WBUserCabinet.user_id)
        .where(User.user_telegram_id == telegram_id)
        .where(WBUserCabinet.wb_cabinet_id == adv_setting.wb_cabinet_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _reload_adv_setting_menu(
    bot: Bot,
    chat_id: int,
    wb_user_cabinet_original_id: int,
    adv_setting_original_id: int,
) -> None:
    async with sm() as session:
        wb_uc = await session.execute(
            select(WBUserCabinet).where(
                WBUserCabinet.id == wb_user_cabinet_original_id
            )
        )
        wb_user_cabinet = wb_uc.scalar_one_or_none()
        adv_r = await session.execute(
            select(AdvSetting)
            .options(joinedload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == adv_setting_original_id)
        )
        adv_setting_reload = adv_r.scalar_one_or_none()

    if wb_user_cabinet and adv_setting_reload:
        await AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting_reload)()


async def _validate_wb_campaign_kind(
    shop_id: str,
    wb_adv_id: int,
    expected: Literal["auto", "auction"],
) -> tuple[bool, str]:
    """
    Проверить, что кампания существует в WB и соответствует ожидаемому типу
    (auto / auction).
    """
    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            factory = (
                container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
            )
            hub = factory.get_wb_manager_hub(shop_id)
            items = await hub.wb_data_manager.promotion_manager.get_adverts_v2_by_ids(
                [wb_adv_id]
            )
    except Exception as e:
        logger.warning("rebind: get_adverts_v2_by_ids failed: %s", e)
        return False, "Не удалось проверить кампанию в WB. Попробуйте позже."

    if not items:
        return False, "Кампания с таким ID не найдена в WB."

    kind = classify_wb_campaign_for_rebind(items[0])
    if kind is None:
        return (
            False,
            "РК не подходит: статус неактивен/завершён или тип не определён.",
        )

    if expected == "auto" and kind != "auto":
        return False, "Указанная РК не является автоматической (полки/рекомендации)."

    if expected == "auction" and kind != "auction":
        return False, "Указанная РК не является поисковой (аукцион)."

    return True, ""


def _rebind_submenu_keyboard(
    adv_setting_original_id: int,
    wb_user_cabinet_original_id: int,
):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text="Изменить Ручную ставку (Поиск-Аукцион)",
            callback_data=callbacks.RebindAdvCampaignIds(
                action="search",
                adv_setting_original_id=adv_setting_original_id,
                wb_user_cabinet_original_id=wb_user_cabinet_original_id,
            ).pack(),
        )
    )
    b.row(
        InlineKeyboardButton(
            text="Изменить Единую ставку (Авто-Полки-Рекомендации)",
            callback_data=callbacks.RebindAdvCampaignIds(
                action="auto",
                adv_setting_original_id=adv_setting_original_id,
                wb_user_cabinet_original_id=wb_user_cabinet_original_id,
            ).pack(),
        )
    )
    b.row(
        InlineKeyboardButton(
            text="К настройкам РК",
            callback_data=callbacks.RebindAdvCampaignIds(
                action="back",
                adv_setting_original_id=adv_setting_original_id,
                wb_user_cabinet_original_id=wb_user_cabinet_original_id,
            ).pack(),
        )
    )
    return b.as_markup()


@router.callback_query(callbacks.RebindAdvCampaignIds.filter(F.action == "menu"))
async def open_rebind_menu(
    callback: CallbackQuery,
    callback_data: callbacks.RebindAdvCampaignIds,
    bot: Bot,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id
    await bot.send_message(
        chat_id,
        "Выберите, что изменить:",
        reply_markup=_rebind_submenu_keyboard(
            callback_data.adv_setting_original_id,
            callback_data.wb_user_cabinet_original_id,
        ),
    )


@router.callback_query(callbacks.RebindAdvCampaignIds.filter(F.action == "back"))
async def rebind_back_to_adv_menu(
    callback: CallbackQuery,
    callback_data: callbacks.RebindAdvCampaignIds,
    bot: Bot,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id
    adv_oid = callback_data.adv_setting_original_id
    wb_uc_oid = callback_data.wb_user_cabinet_original_id

    async with sm() as session:
        result = await session.execute(
            select(AdvSetting)
            .options(joinedload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == adv_oid)
        )
        adv = result.scalar_one_or_none()
    if not adv:
        await bot.send_message(chat_id, "Кампания не найдена.")
        return

    async with sm() as session:
        wb_r = await session.execute(
            select(WBUserCabinet).where(WBUserCabinet.id == wb_uc_oid)
        )
        wb_user_cabinet = wb_r.scalar_one_or_none()

    if not wb_user_cabinet:
        await bot.send_message(chat_id, "Кабинет не найден.")
        return

    await AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()


async def _start_rebind_input_impl(
    callback: CallbackQuery,
    callback_data: callbacks.RebindAdvCampaignIds,
    bot: Bot,
    state: FSMContext,
    *,
    for_auto: bool,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id
    adv_oid = callback_data.adv_setting_original_id
    wb_uc_oid = callback_data.wb_user_cabinet_original_id

    await state.update_data(
        adv_setting_original_id=adv_oid,
        wb_user_cabinet_original_id=wb_uc_oid,
    )

    if for_auto:
        await state.set_state(states.RebindCampaignIds.waiting_for_auto_adv_id)
        prompt = (
            "Введите числовой ID кампании WB в кабинете (целое число).\n"
            "Нужна кампания с единой ставкой: авто, полки, рекомендации (не поиск)."
        )
    else:
        await state.set_state(states.RebindCampaignIds.waiting_for_search_adv_id)
        prompt = (
            "Введите числовой ID кампании WB в кабинете (целое число).\n"
            "Нужна кампания с ручной ставкой в поиске (аукцион)."
        )

    await bot.send_message(chat_id, prompt)


@router.callback_query(callbacks.RebindAdvCampaignIds.filter(F.action == "auto"))
async def start_rebind_auto(
    callback: CallbackQuery,
    callback_data: callbacks.RebindAdvCampaignIds,
    bot: Bot,
    state: FSMContext,
) -> None:
    await _start_rebind_input_impl(
        callback, callback_data, bot, state, for_auto=True
    )


@router.callback_query(callbacks.RebindAdvCampaignIds.filter(F.action == "search"))
async def start_rebind_search(
    callback: CallbackQuery,
    callback_data: callbacks.RebindAdvCampaignIds,
    bot: Bot,
    state: FSMContext,
) -> None:
    await _start_rebind_input_impl(
        callback, callback_data, bot, state, for_auto=False
    )


@router.message(StateFilter(states.RebindCampaignIds.waiting_for_auto_adv_id))
async def apply_auto_adv_id(
    message: Message,
    bot: Bot,
    state: FSMContext,
) -> None:
    await _apply_rebind_message(
        message,
        bot,
        state,
        expected_kind="auto",
        field_setter=_set_adv_id_on_model,
    )


@router.message(StateFilter(states.RebindCampaignIds.waiting_for_search_adv_id))
async def apply_search_adv_id(
    message: Message,
    bot: Bot,
    state: FSMContext,
) -> None:
    await _apply_rebind_message(
        message,
        bot,
        state,
        expected_kind="auction",
        field_setter=_set_search_adv_id_on_model,
    )


def _set_adv_id_on_model(adv: AdvSetting, new_id: int) -> None:
    adv.adv_id = new_id


def _set_search_adv_id_on_model(adv: AdvSetting, new_id: int) -> None:
    adv.search_adv_id = new_id


async def _apply_rebind_message(
    message: Message,
    bot: Bot,
    state: FSMContext,
    expected_kind: Literal["auto", "auction"],
    field_setter,
) -> None:
    chat_id = message.chat.id
    telegram_id = message.from_user.id if message.from_user else 0
    text = message.text or ""

    if "/start" in text:
        await state.clear()
        await start.start_registration(message, bot, state)
        return

    try:
        new_id = int(text.strip())
    except (ValueError, AttributeError):
        await message.answer("Введите целое положительное число — ID кампании WB.")
        return

    if new_id <= 0:
        await message.answer("ID должен быть положительным целым числом.")
        return

    data = await state.get_data()
    adv_oid = data.get("adv_setting_original_id")
    wb_uc_oid = data.get("wb_user_cabinet_original_id")
    if adv_oid is None or wb_uc_oid is None:
        await message.answer(
            "Сессия устарела. Откройте меню кампании и нажмите «Перепривязать кампании WB» снова."
        )
        await state.clear()
        return

    async with sm(read_only=True) as session:
        result = await session.execute(
            select(AdvSetting)
            .options(joinedload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == adv_oid)
        )
        adv_setting = result.scalar_one_or_none()

    if not adv_setting or not adv_setting.wb_cabinet:
        await message.answer("Кампания не найдена.")
        await state.clear()
        return

    shop_id = adv_setting.wb_cabinet.shop_id

    if expected_kind == "auto":
        other = adv_setting.search_adv_id
        if other is not None and new_id == other:
            await message.answer(
                "Этот ID совпадает с текущей поисковой РК. Укажите другую автокампанию."
            )
            return
    else:
        if new_id == adv_setting.adv_id:
            await message.answer(
                "Этот ID совпадает с текущей автокампанией. Укажите другую поисковую РК."
            )
            return

    ok, err = await _validate_wb_campaign_kind(shop_id, new_id, expected_kind)
    if not ok:
        await message.answer(err)
        return

    if expected_kind == "auto":
        async with sm(read_only=True) as session:
            dup = await session.execute(
                select(AdvSetting.id).where(
                    AdvSetting.adv_id == new_id,
                    AdvSetting.id != adv_oid,
                )
            )
            if dup.scalar_one_or_none() is not None:
                await message.answer(
                    "Этот ID автокампании уже привязан к другой записи в системе. "
                    "Сначала освободите его или укажите другую РК."
                )
                return

    rebound_old_id: int | None = None
    try:
        async with sm(read_only=False) as session:
            adv = await session.get(AdvSetting, adv_oid)
            if not adv:
                await message.answer("Кампания не найдена.")
                await state.clear()
                return
            if expected_kind == "auto":
                old_id = adv.adv_id
            else:
                old_id = adv.search_adv_id
            if old_id is not None and old_id != new_id:
                rebound_old_id = old_id
            field_setter(adv, new_id)
            if expected_kind == "auction":
                await ensure_search_adv_setting_for_main_adv(
                    session,
                    adv,
                    new_id,
                    nmids=adv.nmids,
                )
            await session.commit()
        if rebound_old_id is not None:
            await append_rebound_wb_adv_id(adv_oid, expected_kind, rebound_old_id)
    except IntegrityError:
        logger.warning(
            "rebind adv_id integrity error adv_setting_id=%s new_id=%s expected_kind=%s",
            adv_oid,
            new_id,
            expected_kind,
        )
        if expected_kind == "auto":
            await message.answer(
                "Не удалось сохранить: этот ID автокампании уже занят другой записью."
            )
        else:
            await message.answer(
                "Не удалось сохранить: этот ID поисковой РК уже занят другой записью."
            )
        return

    await state.clear()
    if expected_kind == "auto":
        done_text = (
            f"Готово. Обновлена привязка автокампании (единая ставка). "
            f"ID в WB: {new_id}."
        )
    else:
        done_text = (
            f"Готово. Обновлена привязка поисковой РК (ручная ставка). "
            f"ID в WB: {new_id}."
        )
    await message.answer(done_text)

    async with sm() as session:
        result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_oid)
        )
        adv_for_menu = result.scalar_one_or_none()
        if adv_for_menu:
            wb_uc = await _get_wb_user_cabinet_for_adv_and_telegram(
                session, adv_for_menu, telegram_id
            )
            if wb_uc:
                await AdvSettingMenu(bot, chat_id, wb_uc, adv_for_menu)()
                return

    await _reload_adv_setting_menu(bot, chat_id, wb_uc_oid, adv_oid)
