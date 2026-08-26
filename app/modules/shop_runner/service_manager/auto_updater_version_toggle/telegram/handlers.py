"""Telegram-обработчики выбора версии AutoUpdater и PG-меню кампании."""

import logging
from typing import Any, cast

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.views.callbacks import (
    AutoUpdaterVersionMenuBack,
    AutoUpdaterVersionMenuOpen,
    AutoUpdaterVersionToggle,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu import (
    AdvSettingMenu,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard import (
    get_adv_setting_keyboard,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.automatic_version_ui import (
    FSM_ADV_AUTO_VER_MENU_ADV_SETTING_ID,
    FSM_ADV_AUTO_VER_PARENT_MESSAGE_ID,
    build_automatic_version_submenu_markup,
    normalize_automatic_version_ui,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    is_switch_to_version_blocked_by_ab_hold,
)
from app.modules.shop_runner.service_manager.services.v3_status_mode_backfill import (
    backfill_v3_hard_statuses_and_states_consistency,
)
from app.modules.wb_adv_updater import data_manager
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()
logger = logging.getLogger(__name__)

_ALLOWED_AUTOMATIC_VERSIONS: frozenset[int] = frozenset({2, 3})

_VERSION_LABEL: dict[int, str] = {2: "V2", 3: "V3"}

_SUBMENU_TEXT = (
    "Выберите версию АвтоАпдейтера.\n"
    "Текущая отмечена галочкой. «Назад» — снова показать меню РК (это сообщение в чате остаётся)."
)


async def _wb_user_cabinet_for_adv(
    session: AsyncSession,
    adv_setting: AdvSetting,
    telegram_user_id: int,
) -> WBUserCabinet | None:
    stmt = (
        select(WBUserCabinet)
        .options(joinedload(WBUserCabinet.wb_cabinet))
        .join(User, User.id == WBUserCabinet.user_id)
        .where(User.user_telegram_id == telegram_user_id)
        .where(WBUserCabinet.wb_cabinet_id == adv_setting.wb_cabinet_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_adv_for_toggle_in_session(
    session: AsyncSession,
    adv_setting_original_id: int,
) -> AdvSetting | None:
    """Загрузить РК в переданной WRITE-сессии перед переключением версии."""
    result = await session.execute(
        select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
    )
    return result.scalar_one_or_none()


async def _clear_version_menu_fsm(state: FSMContext) -> None:
    await state.update_data(
        {
            FSM_ADV_AUTO_VER_PARENT_MESSAGE_ID: None,
            FSM_ADV_AUTO_VER_MENU_ADV_SETTING_ID: None,
        }
    )


async def _load_adv_for_version_menu(
    session: AsyncSession,
    adv_setting_original_id: int,
) -> AdvSetting | None:
    """Загрузить РК для меню версий в переданной read-only PG-сессии."""
    result = await session.execute(
        select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
    )
    return result.scalar_one_or_none()


@router.callback_query(AutoUpdaterVersionMenuOpen.filter())
async def open_auto_updater_version_menu(
    callback_query: CallbackQuery,
    callback_data: AutoUpdaterVersionMenuOpen,
    bot: Bot,
    state: FSMContext,
) -> None:
    adv_setting_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=True) as session:
        adv = await _load_adv_for_version_menu(session, adv_setting_original_id)
        markup = (
            build_automatic_version_submenu_markup(adv) if adv is not None else None
        )

    if adv is None or markup is None:
        if callback_query.message is not None:
            await bot.send_message(
                callback_query.message.chat.id, "Кампания не найдена."
            )
        return

    assert callback_query.message
    msg = callback_query.message
    chat_id = msg.chat.id
    await state.update_data(
        {
            FSM_ADV_AUTO_VER_PARENT_MESSAGE_ID: msg.message_id,
            FSM_ADV_AUTO_VER_MENU_ADV_SETTING_ID: adv_setting_original_id,
        }
    )
    await bot.send_message(chat_id, _SUBMENU_TEXT, reply_markup=markup)


@router.callback_query(AutoUpdaterVersionMenuBack.filter())
async def close_auto_updater_version_menu(
    callback_query: CallbackQuery,
    bot: Bot,
    state: FSMContext,
) -> None:
    if callback_query.message is None:
        await _clear_version_menu_fsm(state)
        return

    chat_id = callback_query.message.chat.id
    fsm_data = await state.get_data()
    adv_setting_original_id = fsm_data.get(FSM_ADV_AUTO_VER_MENU_ADV_SETTING_ID)

    await _clear_version_menu_fsm(state)

    if adv_setting_original_id is None:
        return

    telegram_user_id = callback_query.from_user.id
    async with sm(read_only=True) as session:
        adv = await _load_adv_for_version_menu(
            session, int(adv_setting_original_id)
        )
        if adv is None:
            return
        wb_uc = await _wb_user_cabinet_for_adv(session, adv, telegram_user_id)

    if wb_uc is None:
        await bot.send_message(
            chat_id,
            "Не удалось определить кабинет. Откройте РК из списка кампаний.",
        )
        return

    await AdvSettingMenu(bot, chat_id, wb_uc, adv)()


@router.callback_query(AutoUpdaterVersionToggle.filter())
async def toggle_auto_updater_version(
    callback_query: CallbackQuery,
    callback_data: AutoUpdaterVersionToggle,
    bot: Bot,
    state: FSMContext,
) -> None:
    new_version = callback_data.new_version
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    if new_version not in _ALLOWED_AUTOMATIC_VERSIONS:
        if callback_query.message is not None:
            await bot.send_message(
                callback_query.message.chat.id, "Недопустимая версия."
            )
        return

    async with sm(read_only=False) as session:
        adv_before = await _load_adv_for_toggle_in_session(
            session, adv_setting_original_id
        )

        if adv_before is None:
            if callback_query.message is not None:
                await bot.send_message(
                    callback_query.message.chat.id, "Кампания не найдена."
                )
            return

        if is_switch_to_version_blocked_by_ab_hold(
            new_version=new_version,
            mode=getattr(adv_before, "card_ab_hold_mode", None),
        ):
            if callback_query.message is not None:
                await bot.send_message(
                    callback_query.message.chat.id,
                    "Нельзя переключить на V2, пока включён режим A/B Hold. "
                    "Сначала отключите A/B Hold (EXIT), затем меняйте версию.",
                )
            return

        current_norm = normalize_automatic_version_ui(adv_before.automatic_version)
        if new_version == current_norm:
            return

        # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"automatic_version": new_version})
        )
        await session.execute(stmt)
        await session.commit()

    if new_version == 3:
        # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
        repaired = await backfill_v3_hard_statuses_and_states_consistency(
            dry_run=False,
            adv_setting_id=adv_setting_original_id,
        )
        if repaired:
            logger.info(
                "V3 enabled: repaired strategy_mode for adv_setting_id=%s keywords=%s",
                adv_setting_original_id,
                repaired,
            )

    fsm_data = await state.get_data()
    parent_msg_id = fsm_data.get(FSM_ADV_AUTO_VER_PARENT_MESSAGE_ID)
    stored_adv_id = fsm_data.get(FSM_ADV_AUTO_VER_MENU_ADV_SETTING_ID)

    submenu_markup: InlineKeyboardMarkup | None = None
    parent_markup: InlineKeyboardMarkup | None = None
    async with sm(read_only=False) as session:
        adv_after = await _load_adv_for_toggle_in_session(
            session, adv_setting_original_id
        )
        if adv_after is None:
            raise RuntimeError(
                f"AdvSetting not found for original_id={adv_setting_original_id}"
            )
        wb_uc = await _wb_user_cabinet_for_adv(
            session, adv_after, callback_query.from_user.id
        )
        submenu_markup = build_automatic_version_submenu_markup(adv_after)
        if (
            parent_msg_id is not None
            and stored_adv_id == adv_setting_original_id
            and wb_uc is not None
        ):
            in_favorites = await data_manager.is_adv_in_favorites(
                adv_after.id, wb_uc.user_id
            )
            parent_markup = get_adv_setting_keyboard(wb_uc, adv_after, in_favorites)

    label = _VERSION_LABEL.get(new_version, f"V{new_version}")

    submenu_msg = callback_query.message
    if not isinstance(submenu_msg, Message):
        return
    chat_id = submenu_msg.chat.id

    # 1) Окно выбора версии: клавиатура строго по данным из БД.
    assert submenu_markup is not None
    try:
        await submenu_msg.edit_reply_markup(reply_markup=submenu_markup)
    except TelegramBadRequest as exc:
        logger.warning("submenu edit_reply_markup failed: %s", exc)

    # 2) Кнопка «сейчас V…» на главном меню РК.
    parent_failed = False
    if parent_markup is not None:
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=int(cast(Any, parent_msg_id)),
                reply_markup=parent_markup,
            )
        except TelegramBadRequest as exc:
            parent_failed = True
            logger.warning(
                "parent edit_message_reply_markup failed chat=%s msg=%s: %s",
                chat_id,
                parent_msg_id,
                exc,
            )

    if parent_failed:
        await bot.send_message(
            chat_id,
            f"Версия {label} сохранена. Если кнопка в главном меню не обновилась — "
            "нажмите «Назад» и откройте настройки РК снова.",
        )
