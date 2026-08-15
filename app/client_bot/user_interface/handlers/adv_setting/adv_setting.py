import logging
import aiogram
from typing import Any, Sequence, cast
from aiogram import Bot, F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import Result, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload

from app.core.di.wb_manager_hub import WBManagerHub, WBManagerHubFactory
from app.modules import balance_manager
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.client_bot.modules.default_settings import apply_defaults_to_adv_setting
from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_menu.message import ShopMenu
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    user_message_after_ordinary_minus_update,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    is_ab_hold_structural_freeze,
)
from app.modules.shop_runner.service_manager.services.minus_phrase_manager import (
    MinusPhraseManagerContainer,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.token_monitoring.services.token_info_service import TokenInfoService
from app.modules.wb_adv_updater import data_manager as wb_data_manager
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

from .... import const
from ... import states
from ...views import callbacks, messages
from ...views.messages.main_adv_setting_menu import AdvSettingMenu
from ...views.messages.main_adv_setting_menu.auto_management_landing import (
    AutoManagementHowItWorks,
    AutoManagementLanding,
)
from ...views.messages.main_adv_setting_menu.minus_phrases_setting import (
    MinusPhrasesSettingScreen,
)

sm = get_async_session_maker

router = Router()


logger = logging.getLogger(__name__)

pricer = Pricer()

READ_ONLY_TOKEN_BOT_ACTIVE_MESSAGE = (
    "У этого токена только права чтения. Автоуправление недоступно. "
    "Вы можете пользоваться аналитикой или заменить токен на ключ с правами управления продвижением."
)


async def _shop_has_read_only_only_tokens(shop_id: str) -> bool:
    """Return True when the shop has only active read-only tokens for analytics."""
    token_status = await TokenInfoService().get_shop_token_status(shop_id)
    has_active_read_only_token = any(
        token.is_read_only and token.is_valid and not token.is_expired
        for token in token_status.all_tokens
    )
    return has_active_read_only_token and not token_status.valid_tokens

 # TODO: Переделать в WBCabinet.get()
async def _get_wb_user_cabinet(
    wb_user_cabinet_original_id: int,
) -> WBUserCabinet:
    """Load WBUserCabinet by id for campaign and landing navigation."""
    async with sm(read_only=True) as session:
        result = await session.execute(
            select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        wb_user_cabinet = result.scalar_one_or_none()
    if wb_user_cabinet is None:
        raise RuntimeError(
            f"WBUserCabinet not found for original_id={wb_user_cabinet_original_id}"
        )
    return wb_user_cabinet

# TODO: переделать в тестируемую функцию

async def _get_adv_setting(adv_setting_original_id: int) -> AdvSetting:
    """Load AdvSetting by id for campaign menu and paid-landing handlers."""
    async with sm(read_only=True) as session:
        result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )
        adv_setting = result.scalar_one_or_none()
    if adv_setting is None:
        raise RuntimeError(
            f"AdvSetting not found for original_id={adv_setting_original_id}"
        )
    return adv_setting


async def _get_adv_setting_or_none(adv_setting_original_id: int) -> AdvSetting:
    """Backward-compatible alias for tests patching the legacy helper name."""
    return await _get_adv_setting(adv_setting_original_id)


async def _get_wb_user_cabinet_or_none(
    wb_user_cabinet_original_id: int,
) -> WBUserCabinet:
    """Backward-compatible alias for tests patching the legacy helper name."""
    return await _get_wb_user_cabinet(wb_user_cabinet_original_id)

async def turn_adv_on_in_session(
    session: AsyncSession,
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: callbacks.TurnBot,
    bot: aiogram.Bot,
) -> None:
    """Включить бота РК в переданной WRITE session и сохранить изменения в PG.

    Parent ``turn_adv_on`` открывает ``sm(read_only=False)`` и передаёт session
    сюда. Здесь выполняются загрузка кабинета и кампании, проверка баланса,
    запись ``bot_active=True``, commit и повторная загрузка кабинета для меню.
    """
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    adv_original_id = callback_data.adv_original_id
    stmt = (
        select(WBUserCabinet)
        .join(WBUserCabinet.wb_cabinet)
        .options(selectinload(WBUserCabinet.wb_cabinet))
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
    )
    result_for_wb_user_cabinet = await session.execute(stmt)
    wb_user_cabinet: WBUserCabinet = result_for_wb_user_cabinet.scalar_one()
    stmt = (
        select(AdvSetting)
        .options(selectinload(AdvSetting.payments))
        .where(AdvSetting.id == adv_original_id)
    )
    result_for_adv_setting = await session.execute(stmt)
    adv: AdvSetting = result_for_adv_setting.scalar_one()
    wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet
    tariff_for_month: int | float = await pricer.get_price_for_day_for_shop(
        session, wb_cabinet.shop_id
    )
    price_for_adv_for_day = pricer.get_tariff_for_day(int(tariff_for_month))
    balance, bonus = await balance_manager.get_cabinet_balance_and_bonuses(
        wb_cabinet.id
    )
    sum_balance = balance + bonus
    if sum_balance <= 0:
        _ = await bot.send_message(
            chat_id,
            "Недостаточно средств на балансе кабинета для запуска. Пополните баланс.",
        )
        _ = await ShopMenu(
            bot, chat_id, state, wb_user_cabinet_original_id
        )()
        return
    if not sum_balance >= price_for_adv_for_day:
        _ = await bot.send_message(chat_id, "Недостаточно средств")
        _ = await ShopMenu(
            bot, chat_id, state, wb_user_cabinet_original_id
        )()
        return
    if await _shop_has_read_only_only_tokens(wb_cabinet.shop_id):
        _ = await bot.send_message(chat_id, READ_ONLY_TOKEN_BOT_ACTIVE_MESSAGE)
        _ = await ShopMenu(
            bot, chat_id, state, wb_user_cabinet_original_id
        )()
        return
    _ = await bot.send_message(chat_id, "Включаю бота")
    adv.bot_active = True
    await session.commit()
    _ = await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    _ = await state.update_data(adv_original_id=adv.id)
    stmt = select(WBUserCabinet).where(
        WBUserCabinet.id == wb_user_cabinet_original_id
    )
    result: Result[tuple[WBUserCabinet]] = await session.execute(stmt)
    wb_user_cabinet = result.scalar_one()
    _ = await AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()


@router.callback_query(callbacks.ChoiceAdvPaginator.filter(F.reset_filter))
async def reset_filter(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.update_data(filter_advs=[])

    async with sm() as session:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt)
        adv_settings = list(result.scalars().all())

    page = 1
    message = callback.message
    assert message
    await messages.AdvCompanyChoicing(
        bot,
        message.chat.id,
        wb_user_cabinet_original_id,
        adv_settings,
        state,
        page=page,
    )()

    return


@router.message(StateFilter(states.AdvCompanyCatalog.waiting_for_keywords_for_filter))
async def waiting_for_keywords_for_filter(
    message: types.Message, bot: Bot, state: FSMContext
):
    chat_id = message.chat.id
    if not (text := message.text):
        await message.answer('Не получен список ключей')
        return None
    filter_advs: list[str] = text.splitlines()
    filter_advs = [keyword.strip().lower() for keyword in filter_advs if keyword]
    await state.update_data(filter_advs=filter_advs)
    state_data = await state.get_data()
    wb_user_cabinet_original_id: int = state_data["last_wb_user_cabinet_original_id"]
    async with sm() as session:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = list(result.scalars().all())

    page = 1
    check_data = await state.get_data()
    logger.debug("check_data: %s", check_data)
    await messages.AdvCompanyChoicing(
        bot, chat_id, wb_user_cabinet_original_id, adv_settings, state, page=page
    )()
    return None


@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def choice_adv_paginator(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
):
    if callback.message is None:
        raise ValueError('Нет сообщения')
    chat_id: int = callback.message.chat.id
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(
        state=states.AdvCompanyCatalog.waiting_for_keywords_for_filter
    )
    page = callback_data.page
    check_data = await state.get_data()
    logger.debug("check_data: %s", check_data)
    stmt = (
        select(AdvSetting)
        .join(AdvSetting.wb_cabinet)
        .join(WBCabinet.wb_user_cabinets)
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
    )
    async with sm() as session:
        result = await session.execute(stmt)
        adv_settings = list(result.scalars().all())
    await messages.AdvCompanyChoicing(
        bot, chat_id, wb_user_cabinet_original_id, adv_settings, state, page=page
    )()
    return


@router.callback_query(callbacks.Adv.filter())
async def adv_handler(
    callback: types.CallbackQuery,
    callback_data: callbacks.Adv,
    bot: aiogram.Bot,
    state: FSMContext,
):
    if callback.message is None:
        raise ValueError('Нет сообщения')
    chat_id = callback.message.chat.id
    await state.set_state()
    await messages.LongTimeOperation(bot, callback.message.chat.id)()
    adv_original_id = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id)
    data = await state.get_data()

    try:
        wb_user_cabinet_original_id = data["last_wb_user_cabinet_original_id"]
    except KeyError:
        async with sm() as session:
            stmt = (
                select(WBUserCabinet)
                .join(WBUserCabinet.user)
                .join(WBUserCabinet.wb_cabinet)
                .join(WBCabinet.adv_settings)
                .filter(
                    User.user_telegram_id
                    == callback.from_user.id,  # Фильтрация по user_telegram_id
                    AdvSetting.id
                    == adv_original_id,  # Фильтрация по нужному AdvSetting
                )
            )
            result = await session.execute(stmt)
            wb_user_cabinet = result.scalar_one()  # Извлекаем первую строку
        wb_user_cabinet_original_id: int = wb_user_cabinet.id

    async with sm() as session:
        adv_result: Result[tuple[AdvSetting]] = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv: AdvSetting | None = adv_result.scalar_one_or_none()

    if not adv:
        raise RuntimeError(
            f"AdvSetting not found for original_id={adv_original_id}"
        )

    # TODO: Перенести в отдельную функцию
    async with sm(read_only=True) as session:
        stmt = (
            select(WBUserCabinet)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
            .options(selectinload(WBUserCabinet.wb_cabinet))
        )
        wb_user_cabinet_result = await session.execute(stmt)
        wb_user_cabinet = wb_user_cabinet_result.scalar_one()

    if not wb_user_cabinet:
        raise RuntimeError(
            f"WBUserCabinet not found for original_id={wb_user_cabinet_original_id}"
        )

    nmids = adv.nmids or []
    nmid = nmids[0] if nmids else None
    if nmid is None:
        _ = await bot.send_message(
            chat_id,
            "Не удалось открыть РК: у кампании отсутствует артикул. "
            f"Обратитесь в поддержку -> {const.SUPPORT_LINK}",
        )
        return
    shop_id = str(wb_user_cabinet.wb_cabinet.shop_id)
    ui_card_result = await wb_data_manager.ensure_card_with_image_for_ui(shop_id, nmid)
    if not ui_card_result.ok:
        _ = await bot.send_message(
            chat_id,
            "Не удалось загрузить данные карточки для отображения РК. "
            "Переход в меню остановлен до восстановления данных. "
            f"Обратитесь в поддержку -> {const.SUPPORT_LINK}",
        )
        return

    await AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()
    return


@router.callback_query(callbacks.AutoManagementLanding.filter(F.action == "open"))
async def open_auto_management_landing(
    callback: types.CallbackQuery,
    callback_data: callbacks.AutoManagementLanding,
    bot: aiogram.Bot,
) -> None:
    """Open the paid-landing screen instead of toggling bot_active from menu."""
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id

    wb_user_cabinet = await _get_wb_user_cabinet_or_none(
        callback_data.wb_user_cabinet_original_id
    )
    adv_setting = await _get_adv_setting_or_none(
        callback_data.adv_setting_original_id
    )

    await AutoManagementLanding(bot, chat_id, wb_user_cabinet, adv_setting)()


@router.callback_query(callbacks.AutoManagementLanding.filter(F.action == "how"))
async def open_auto_management_how_it_works(
    callback: types.CallbackQuery,
    callback_data: callbacks.AutoManagementLanding,
    bot: aiogram.Bot,
) -> None:
    """Show the detailed explanation screen for paid auto-management."""
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id

    wb_user_cabinet = await _get_wb_user_cabinet_or_none(
        callback_data.wb_user_cabinet_original_id
    )
    adv_setting = await _get_adv_setting_or_none(
        callback_data.adv_setting_original_id
    )

    await AutoManagementHowItWorks(bot, chat_id, wb_user_cabinet, adv_setting)()


@router.callback_query(callbacks.AutoManagementLanding.filter(F.action == "back"))
async def back_from_auto_management_landing(
    callback: types.CallbackQuery,
    callback_data: callbacks.AutoManagementLanding,
    bot: aiogram.Bot,
) -> None:
    """Return from the paid-landing screen back to the campaign menu."""
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id

    wb_user_cabinet = await _get_wb_user_cabinet_or_none(
        callback_data.wb_user_cabinet_original_id
    )
    adv_setting = await _get_adv_setting_or_none(
        callback_data.adv_setting_original_id
    )

    await AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting)()


@router.callback_query(callbacks.MinusPhrasesSetting.filter(F.action == "open"))
async def open_minus_phrases_setting_screen(
    callback: types.CallbackQuery,
    callback_data: callbacks.MinusPhrasesSetting,
    bot: aiogram.Bot,
) -> None:
    """Open the dedicated minus-phrase background sync settings screen."""
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id

    wb_user_cabinet = await _get_wb_user_cabinet_or_none(
        callback_data.wb_user_cabinet_original_id
    )
    adv_setting = await _get_adv_setting_or_none(
        callback_data.adv_setting_original_id
    )

    await MinusPhrasesSettingScreen(bot, chat_id, wb_user_cabinet, adv_setting)()


async def _update_and_get_adv_setting(session: AsyncSession,
                                      new_status: bool,
                                      adv_setting_original_id: int) -> AdvSetting:
    stmt = (
        update(AdvSetting)
        .where(AdvSetting.id == adv_setting_original_id)
        .values(auto_update_minus_phrases=new_status)
        .returning(AdvSetting)
    )

    result = await session.execute(stmt)
    adv_setting = result.scalar_one_or_none()

    if adv_setting is None:
        raise RuntimeError(
            "AdvSetting not found for original_id="
            f"{adv_setting_original_id}"
        )

    await session.commit()
    return adv_setting



@router.callback_query(callbacks.MinusPhrasesSetting.filter(F.action.in_(("on", "off"))))
async def toggle_minus_phrases_setting(
    callback: types.CallbackQuery,
    callback_data: callbacks.MinusPhrasesSetting,
    bot: aiogram.Bot,
) -> None:
    """Toggle only AdvSetting.auto_update_minus_phrases and reopen the settings screen."""
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id
    new_status = callback_data.action == "on"

    wb_user_cabinet = await _get_wb_user_cabinet_or_none(
        callback_data.wb_user_cabinet_original_id
    )
    async with sm(read_only=False) as session:
        adv_setting = await _update_and_get_adv_setting(
            session,
            new_status,
            callback_data.adv_setting_original_id,
        )

    await MinusPhrasesSettingScreen(bot, chat_id, wb_user_cabinet, adv_setting)()


@router.callback_query(callbacks.MinusPhrasesSetting.filter(F.action == "back"))
async def back_from_minus_phrases_setting(
    callback: types.CallbackQuery,
    callback_data: callbacks.MinusPhrasesSetting,
    bot: aiogram.Bot,
) -> None:
    """Return from the minus-phrase settings screen back to the campaign menu."""
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id

    wb_user_cabinet = await _get_wb_user_cabinet_or_none(
        callback_data.wb_user_cabinet_original_id
    )
    adv_setting = await _get_adv_setting(
        callback_data.adv_setting_original_id
    )

    await AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting)()


@router.callback_query(callbacks.TurnBot.filter(F.action == "on"))
async def turn_adv_on(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: callbacks.TurnBot,
    bot: aiogram.Bot,
) -> None:
    if callback.message is None:
        raise ValueError('Нет сообщения')
    async with sm(read_only=False) as session:
        await turn_adv_on_in_session(session, callback, state, callback_data, bot)
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == "off_all"))
async def turn_adv_off_all(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: callbacks.TurnBot,
    bot: aiogram.Bot,
):
    if callback.message is None:
        raise ValueError('Нет сообщения')

    chat_id = callback.message.chat.id

    await bot.send_message(callback.message.chat.id, "Отключаю бота от всех кампаний")
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm(read_only=False) as session:
        advs = await session.execute(
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        advs = advs.scalars().all()
        for adv_ in advs:
            adv_.bot_active = False
        await session.commit()
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == "off"))
async def turn_adv_off(
    call: types.CallbackQuery, callback_data: callbacks.TurnBot, bot: aiogram.Bot
):
    if call.message is None:
        raise ValueError('Нет сообщения')

    chat_id = call.message.chat.id

    # data = await state.get_data()
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = (
            select(WBUserCabinet)
            .join(WBUserCabinet.wb_cabinet)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet = wb_user_cabinet.scalar()

    if not wb_user_cabinet:
        raise RuntimeError(
            f"WBUserCabinet not found for original_id={wb_user_cabinet_original_id}"
        )

    async with sm(read_only=False) as session:
        result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == callback_data.adv_original_id)
        )
        adv_setting: AdvSetting = result.scalar_one()
        adv_setting.bot_active = False
        await session.commit()

    await AdvSettingMenu(
        bot,
        chat_id,
        wb_user_cabinet,
        adv_setting,
    )()

@router.callback_query(callbacks.ApplyCampaignDefaults.filter())
async def apply_campaign_defaults(
    callback: types.CallbackQuery,
    callback_data: callbacks.ApplyCampaignDefaults,
    bot: aiogram.Bot,
) -> None:
    if callback.message is None:
        raise ValueError('Нет сообщения')
    chat_id = callback.message.chat.id

    adv_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        result = await session.execute(
            select(AdvSetting)
            .options(joinedload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == adv_original_id)
        )
        adv_setting: AdvSetting = result.scalar_one()

        # spec card-ab-hold-mode «Shared defaults MUST NOT disable or mutate A/B
        # Hold on a held campaign» / decision §13: «Применить дефолты» — не
        # disable-path. Для PENDING_SETUP/ACTIVE не применяем дефолты (иначе
        # un-owned disable: mode→off + stale snapshot + сброс V3/structural).
        # Отключение A/B Hold — только owned Telegram EXIT на экране режима.
        if is_ab_hold_structural_freeze(adv_setting.card_ab_hold_mode):
            await bot.send_message(
                chat_id,
                "Кампания в режиме A/B Hold — дефолтные настройки не применены. "
                "Сначала выключите A/B Hold на экране режима, затем повторите.",
            )
        else:
            # Применяем дефолты через ORM
            apply_defaults_to_adv_setting(adv_setting, adv_setting.wb_cabinet)
            await session.commit()

            await bot.send_message(
                chat_id, "Дефолтные настройки применены успешно!"
            )

        # Обновить меню кампании
        wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
        async with sm() as session_read:
            wb_user_cabinet = await session_read.execute(
                select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
            )
            wb_user_cabinet = wb_user_cabinet.scalar()

        if not wb_user_cabinet:
            raise RuntimeError(
                "WBUserCabinet not found for original_id="
                f"{wb_user_cabinet_original_id}"
            )

        await AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting)()

    return


@router.callback_query(callbacks.WBUpdate.filter(F.action == "update_minus_keywords"))
async def wb_update_minus_keywords(
    callback: types.CallbackQuery,
    callback_data: callbacks.WBUpdate,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Ручное «Обновить минус-слова»; при A/B Hold freeze — non-success UX (spec §10)."""
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id
    adv_setting_original_id = callback_data.adv_setting_original_id

    await bot.send_message(chat_id, "Обновляю минус-слова…")

    async with sm(read_only=True) as session:
        result = await session.execute(
            select(AdvSetting)
            .options(joinedload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == adv_setting_original_id)
        )
        adv_setting: AdvSetting | None = result.scalar_one_or_none()

    if adv_setting is None:
        raise RuntimeError(
            f"AdvSetting not found for original_id={adv_setting_original_id}"
        )
    wb_cabinet = getattr(adv_setting, "wb_cabinet", None)
    if wb_cabinet is None:
        raise RuntimeError(
            f"WBCabinet missing for AdvSetting original_id={adv_setting_original_id}"
        )
    shop_id = wb_cabinet.shop_id
    if not shop_id:
        raise RuntimeError(
            f"WBCabinet shop_id missing for adv_setting_original_id={adv_setting_original_id}"
        )

    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            factory = cast(
                WBManagerHubFactory,
                container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory(), # pyright: ignore
            )
            hub: WBManagerHub  = factory.get_wb_manager_hub(shop_id)
            tasks_manager = TasksManager(max_workers=1)
            redis_client_wrapper = cast(
                RedisClient,
                cast(Any, container).redis_client_wrapper(),
            )
            wb_shop_data_manager = WBShopDataManager(
                wb_cabinet=wb_cabinet,
                tasks_manager=tasks_manager,
                wb_api_data_manager=hub.wb_data_manager,
                wb_manager=hub.wb_manager,
                plan_fact_reader=PlanFactReader(redis_client=redis_client_wrapper),
            )
            complex_advs = await wb_shop_data_manager.get_complex_advs(
                load_extras=False
            )
            complex_adv = next(
                (a for a in complex_advs if a.adv_setting_original_id == adv_setting_original_id),
                None,
            )
            if complex_adv is None:
                raise RuntimeError(
                    "ComplexAdv not found for adv_setting_original_id="
                    f"{adv_setting_original_id}"
                )
            elif not complex_adv.bot_active:
                await bot.send_message(
                    chat_id,
                    "Включите бота для кампании, затем повторите обновление минус-слов.",
                )
            else:
                minus_phrase_manager = MinusPhraseManagerContainer(
                    _wb_api_manager_hub=hub
                ).minus_phrase_manager()
                # Spec §10 / decision §8: freeze skip → non-success Telegram copy.
                applied = await minus_phrase_manager.update_minus_phrases(
                    complex_adv
                )
                await bot.send_message(
                    chat_id,
                    user_message_after_ordinary_minus_update(applied=applied),
                )
    except RuntimeError:
        raise
    except Exception:
        logger.exception("Ошибка обновления минус-слов для adv_setting_id=%s", adv_setting_original_id)
        await bot.send_message(
            chat_id,
            f"Не удалось обновить минус-слова, обратитесь в поддержку -> {const.SUPPORT_LINK} \n\n",
        )

    data = await state.get_data()
    wb_user_cabinet_id = data.get("last_wb_user_cabinet_original_id")
    if wb_user_cabinet_id is not None:
        async with sm(read_only=True) as session:
            result = await session.execute(
                select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_id)
            )
            wb_user_cabinet = result.scalar_one_or_none()
        if wb_user_cabinet is not None:
            await AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting)()


@router.callback_query(callbacks.ApplyDefaultsForShop.filter())
async def apply_defaults_for_shop(
    callback: types.CallbackQuery,
    callback_data: callbacks.ApplyDefaultsForShop,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    if callback.message is None:
        raise ValueError('Нет сообщения')
    chat_id: int = callback.message.chat.id

    async with sm(read_only=False) as session:
        # Получаем только активные кампании магазина через ORM
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .options(selectinload(AdvSetting.wb_cabinet))
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
            .where(AdvSetting.bot_active.is_(True))
        )
        result: Result[tuple[AdvSetting]] = await session.execute(stmt)
        adv_settings: Sequence[AdvSetting] = result.scalars().all()

        # Применяем дефолты через ORM для каждой активной кампании.
        # spec card-ab-hold-mode / decision §13: held (PENDING_SETUP/ACTIVE)
        # кампании пропускаем — «Применить дефолты» не отключает A/B Hold
        # (disable только через owned Telegram EXIT); non-held получают дефолты.
        updated_count = 0
        skipped_ab_hold = 0
        for adv_setting in adv_settings:
            if is_ab_hold_structural_freeze(adv_setting.card_ab_hold_mode):
                skipped_ab_hold += 1
                continue
            apply_defaults_to_adv_setting(adv_setting,
                                         adv_setting.wb_cabinet)
            updated_count += 1

        await session.commit()

    message_text = (
        f"Дефолтные настройки применены к {updated_count} активным кампаниям магазина."
    )
    if skipped_ab_hold:
        message_text += (
            f"\nПропущено кампаний в режиме A/B Hold: {skipped_ab_hold}. "
            "Чтобы применить дефолты к ним, сначала выключите A/B Hold."
        )
    await bot.send_message(chat_id, message_text)

    # Вернуть пользователя в меню магазина
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()

    return


@router.callback_query(callbacks.ResetShopNonRelevantPhrases.filter())
async def reset_shop_non_relevant_phrases(
    callback: types.CallbackQuery,
    callback_data: callbacks.ResetShopNonRelevantPhrases,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Сбрасывает shop-wide NRF hard_status; held кампании пропускает updater.

    ``update_keywords`` excludes ``is_ab_hold_structural_freeze`` campaigns
    (FINDING-PBH-010-R1; peer apply_defaults skip). Telegram copy mirrors
    ``apply_defaults_for_shop``: Hold-skip claim only when skipped_count > 0
    (ROOT-001).
    """
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm(read_only=False) as session:
        from .utils import update_keywords

        update_result = await update_keywords(
            session, wb_user_cabinet_original_id
        )

    updated_count = int(update_result)
    # Plain int mocks / legacy returns → no skip signal (treat as 0).
    skipped_count = int(getattr(update_result, "skipped_count", 0) or 0)

    message_text = f"Сброшено НРФ: {updated_count}."
    if skipped_count > 0:
        message_text += (
            f" Кампании в A/B Hold пропущены: {skipped_count}."
            " Чтобы сбросить НРФ и для них, сначала выключите A/B Hold."
        )
    message_text += " Возвращаю в меню магазина..."
    await bot.send_message(chat_id, message_text)
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
