"""Telegram UI для управления ставкой в полках (main/settings/FSM/actions).

CallbackQuery: ответ на кнопку даёт ``CallbackAnswerMiddleware`` в ``global_router``
(``pre=True``). В хендлерах этого модуля ``callback.answer()`` не вызываем.
"""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dependency_injector.wiring import Provide, inject
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.client_bot.user_interface import states
from app.client_bot.user_interface.helpers.wb_user_cabinet import (
    get_wb_user_cabinet_for_adv_and_telegram,
)
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    BID_POINT_VIEWER_HEADER,
    build_auto_shelf_bid_control_keyboard,
    build_auto_shelf_bid_settings_keyboard,
    build_auto_shelf_bid_strategy_keyboard,
    bid_point_viewer_page_count,
    build_bid_point_viewer_keyboard,
    clamp_bid_point_page,
    render_auto_shelf_bid_control_message,
    render_auto_shelf_bid_settings_message,
    render_auto_shelf_bid_strategy_message,
    render_bid_point_viewer_message,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu import AdvSettingMenu
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager import (
    AutoShelfBidControlTelegramError,
    AutoShelfBidControlTelegramService,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


def _tg_message(callback: CallbackQuery) -> Message | None:
    """Вернуть Message из callback, исключая InaccessibleMessage."""
    message = callback.message
    return message if isinstance(message, Message) else None


def _asb_exhausted_reset_filter(callback: CallbackQuery) -> bool:
    """Фильтр callback сброса паузы shelf-exhausted."""
    data = callback.data
    return bool(data) and str(data).startswith("asb_exh_reset:")


async def _show_bid_point_viewer(
    callback: CallbackQuery,
    *,
    service: AutoShelfBidControlTelegramService,
    adv_setting_original_id: int,
    index: int,
) -> bool:
    """Показать или обновить просмотрщик покрытой ставки цикла.

    Returns:
        True, если экран показан; False, если покрытий нет.
    """
    view = await service.build_view(adv_setting_original_id)
    points = view.coverage_bid_rows
    if not points:
        return False
    total_pages = bid_point_viewer_page_count(len(points))
    safe_page = clamp_bid_point_page(index, total_pages)
    text = render_bid_point_viewer_message(
        safe_page,
        points,
        currency=view.currency,
        optimization_metric=view.optimization_metric,
    )
    keyboard = build_bid_point_viewer_keyboard(
        adv_setting_original_id,
        safe_page,
        len(points),
    )
    message = _tg_message(callback)
    if message is None:
        return True
    is_viewer_message = (
        message.text is not None
        and BID_POINT_VIEWER_HEADER in message.text
    )
    if is_viewer_message:
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise
    else:
        await message.answer(text, reply_markup=keyboard)
    return True


async def _send_main_screen(
    callback: CallbackQuery,
    *,
    service: AutoShelfBidControlTelegramService,
    adv_setting_original_id: int,
) -> None:
    await service.apply_main_bid_refresh_if_needed(adv_setting_original_id)
    view = await service.build_view(adv_setting_original_id)
    text = render_auto_shelf_bid_control_message(view)
    keyboard = build_auto_shelf_bid_control_keyboard(view, adv_setting_original_id)
    message = _tg_message(callback)
    if message:
        await message.answer(text, reply_markup=keyboard)


async def _send_settings_screen(
    callback: CallbackQuery,
    *,
    service: AutoShelfBidControlTelegramService,
    adv_setting_original_id: int,
) -> None:
    view = await service.build_view(adv_setting_original_id)
    text = render_auto_shelf_bid_settings_message(view)
    keyboard = build_auto_shelf_bid_settings_keyboard(view, adv_setting_original_id)
    message = _tg_message(callback)
    if message:
        await message.answer(text, reply_markup=keyboard)


async def _send_strategy_screen(
    callback: CallbackQuery,
    *,
    service: AutoShelfBidControlTelegramService,
    adv_setting_original_id: int,
) -> None:
    view = await service.build_view(adv_setting_original_id)
    text = render_auto_shelf_bid_strategy_message(view)
    keyboard = build_auto_shelf_bid_strategy_keyboard(view, adv_setting_original_id)
    message = _tg_message(callback)
    if message:
        await message.answer(text, reply_markup=keyboard)


async def _reload_adv_setting_menu(
    bot: Bot,
    chat_id: int,
    adv_setting_original_id: int,
    user_telegram_id: int,
) -> None:
    """Вернуть пользователя в меню настройки РК."""
    async with sm(read_only=True) as session:
        adv_stmt = (
            select(AdvSetting)
            .options(joinedload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == adv_setting_original_id)
        )
        adv_setting = (await session.execute(adv_stmt)).scalar_one_or_none()
        if adv_setting is None:
            await bot.send_message(chat_id, "Кампания не найдена.")
            return
        wb_user_cabinet = await get_wb_user_cabinet_for_adv_and_telegram(
            session,
            adv_setting,
            user_telegram_id,
        )
        if wb_user_cabinet is None:
            await bot.send_message(chat_id, "Кабинет кампании не найден.")
            return
    await AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting)()


@router.callback_query(callbacks.AutoShelfBidControlBidPoints.filter())
@inject
async def auto_shelf_bid_control_bid_points_router(
    callback: CallbackQuery,
    callback_data: callbacks.AutoShelfBidControlBidPoints,
    redis_client: RedisClient = Provide["redis_client_wrapper"],
) -> None:
    """Навигация по покрытым ставкам текущего цикла."""
    service = AutoShelfBidControlTelegramService(redis_client=redis_client)
    try:
        shown = await _show_bid_point_viewer(
            callback,
            service=service,
            adv_setting_original_id=callback_data.adv_setting_original_id,
            index=callback_data.index,
        )
        if not shown:
            message = _tg_message(callback)
            if message:
                await message.answer(
                    "В покрытии ставок теста пока нет доступных строк."
                )
    except AutoShelfBidControlTelegramError as exc:
        message = _tg_message(callback)
        if message:
            await message.answer(exc.message)


@router.callback_query(callbacks.AutoShelfBidControlMenu.filter())
@inject
async def auto_shelf_bid_control_menu_router(
    callback: CallbackQuery,
    callback_data: callbacks.AutoShelfBidControlMenu,
    state: FSMContext,
    bot: Bot,
    redis_client: RedisClient = Provide["redis_client_wrapper"],
) -> None:
    """Маршрутизация callback actions для Telegram-управления ставкой в полках."""
    action = callbacks.normalize_auto_shelf_bid_control_action(callback_data.action)
    adv_setting_original_id = callback_data.adv_setting_original_id
    service = AutoShelfBidControlTelegramService(redis_client=redis_client)
    guarded_write_actions = {
        "enable",
        "disable",
        "reset_cycle",
        "force_main",
        "set_max_bid",
        "set_test_share",
        "set_target_test_impressions",
        "set_target_test_observation_minutes",
        "set_min_bid_distance",
    }
    try:
        if action in guarded_write_actions:
            await service.ensure_write_allowed(adv_setting_original_id)
        if action in {"open", "refresh"}:
            await _send_main_screen(
                callback,
                service=service,
                adv_setting_original_id=adv_setting_original_id,
            )
        elif action == "settings":
            await _send_settings_screen(
                callback,
                service=service,
                adv_setting_original_id=adv_setting_original_id,
            )
        elif action == "strategy_menu":
            await _send_strategy_screen(
                callback,
                service=service,
                adv_setting_original_id=adv_setting_original_id,
            )
        elif action == "enable":
            _ = await service.enable(adv_setting_original_id)
            message = _tg_message(callback)
            if message:
                await message.answer("Управление включено.")
            await _send_main_screen(
                callback,
                service=service,
                adv_setting_original_id=adv_setting_original_id,
            )
        elif action == "disable":
            _ = await service.disable(adv_setting_original_id)
            message = _tg_message(callback)
            if message:
                await message.answer("Управление выключено.")
            await _send_main_screen(
                callback,
                service=service,
                adv_setting_original_id=adv_setting_original_id,
            )
        elif action == "reset_cycle":
            _ = await service.reset_cycle(adv_setting_original_id)
            message = _tg_message(callback)
            if message:
                await message.answer("Цикл сброшен.")
            await _send_main_screen(
                callback,
                service=service,
                adv_setting_original_id=adv_setting_original_id,
            )
        elif action == "force_main":
            _ = await service.force_main(adv_setting_original_id)
            message = _tg_message(callback)
            if message:
                await message.answer("Режим main применён.")
            await _send_main_screen(
                callback,
                service=service,
                adv_setting_original_id=adv_setting_original_id,
            )
        elif action == "set_max_bid":
            await state.update_data(adv_setting_original_id=adv_setting_original_id)
            await state.set_state(states.AutoShelfBidControlFSM.waiting_for_max_bid)
            message = _tg_message(callback)
            if message:
                await message.answer(
                    "Введите максимальную ставку для полок, в рублях.\nНапример: 500"
                )
        elif action == "set_test_share":
            await state.update_data(adv_setting_original_id=adv_setting_original_id)
            await state.set_state(states.AutoShelfBidControlFSM.waiting_for_test_share)
            message = _tg_message(callback)
            if message:
                await message.answer(
                    "Введите долю теста.\nМожно в процентах: 10\nИли долей: 0.1\n"
                    "Допустимо: больше 0 и не больше 49%."
                )
        elif action == "set_target_test_impressions":
            await state.update_data(adv_setting_original_id=adv_setting_original_id)
            await state.set_state(
                states.AutoShelfBidControlFSM.waiting_for_target_test_impressions
            )
            message = _tg_message(callback)
            if message:
                await message.answer(
                    "Введите количество показов на одну тестовую ставку.\nНапример: 500"
                )
        elif action == "set_target_test_observation_minutes":
            await state.update_data(adv_setting_original_id=adv_setting_original_id)
            await state.set_state(
                states.AutoShelfBidControlFSM.waiting_for_target_test_observation_minutes
            )
            message = _tg_message(callback)
            if message:
                await message.answer(
                    "Введите минимальное время теста в минутах.\nПример: 60\nМинимум: 60 минут."
                )
        elif action == "set_min_bid_distance":
            await state.update_data(adv_setting_original_id=adv_setting_original_id)
            await state.set_state(
                states.AutoShelfBidControlFSM.waiting_for_min_bid_distance
            )
            message = _tg_message(callback)
            if message:
                await message.answer(
                    "Введите минимальный шаг между тестовыми ставками, в рублях.\n"
                    "Например: 1"
                )
        elif action == "set_retest_interval_days":
            await state.update_data(adv_setting_original_id=adv_setting_original_id)
            await state.set_state(
                states.AutoShelfBidControlFSM.waiting_for_retest_interval_days
            )
            message = _tg_message(callback)
            if message:
                await message.answer(
                    "Введите интервал перетеста в сутках (целое ≥ 1).\n"
                    "По умолчанию: 7"
                )
        elif action in {
            "set_strategy_plan_distance",
            "set_strategy_ctr",
            "set_strategy_cpc",
        }:
            strategy = {
                "set_strategy_plan_distance": AutoShelfBidControlStrategy.PLAN_DISTANCE,
                "set_strategy_ctr": AutoShelfBidControlStrategy.CTR,
                "set_strategy_cpc": AutoShelfBidControlStrategy.CPC,
            }[action]
            _ = await service.set_strategy(adv_setting_original_id, strategy)
            view = await service.build_view(adv_setting_original_id)
            text = render_auto_shelf_bid_strategy_message(view)
            keyboard = build_auto_shelf_bid_strategy_keyboard(
                view, adv_setting_original_id
            )
            message = _tg_message(callback)
            if message:
                try:
                    await message.edit_text(text, reply_markup=keyboard)
                except TelegramBadRequest as exc:
                    if "message is not modified" not in str(exc).lower():
                        raise
        elif action == "back":
            message = _tg_message(callback)
            if message and callback.from_user:
                await _reload_adv_setting_menu(
                    bot,
                    message.chat.id,
                    adv_setting_original_id,
                    callback.from_user.id,
                )
        else:
            message = _tg_message(callback)
            if message:
                await message.answer("Неизвестное действие.")
            return
    except AutoShelfBidControlTelegramError as exc:
        message = _tg_message(callback)
        if message:
            await message.answer(exc.message)


async def _handle_fsm_update(
    *,
    message: Message,
    state: FSMContext,
    redis_client: RedisClient,
    update_method: str,
) -> None:
    data = await state.get_data()
    adv_setting_original_id = data.get("adv_setting_original_id")
    if not adv_setting_original_id:
        await message.answer("Не найден контекст кампании. Откройте экран заново.")
        await state.clear()
        return
    service = AutoShelfBidControlTelegramService(redis_client=redis_client)
    try:
        method = getattr(service, update_method)
        _ = await method(int(adv_setting_original_id), message.text or "")
    except AutoShelfBidControlTelegramError as exc:
        await message.answer(exc.message)
        return
    await message.answer("Настройка сохранена.")
    view = await service.build_view(int(adv_setting_original_id))
    text = render_auto_shelf_bid_settings_message(view)
    keyboard = build_auto_shelf_bid_settings_keyboard(view, int(adv_setting_original_id))
    await message.answer(text, reply_markup=keyboard)
    await state.clear()


@router.message(StateFilter(states.AutoShelfBidControlFSM.waiting_for_max_bid))
@inject
async def auto_shelf_waiting_for_max_bid(
    message: Message,
    state: FSMContext,
    redis_client: RedisClient = Provide["redis_client_wrapper"],
) -> None:
    await _handle_fsm_update(
        message=message,
        state=state,
        redis_client=redis_client,
        update_method="update_max_bid",
    )


@router.message(StateFilter(states.AutoShelfBidControlFSM.waiting_for_test_share))
@inject
async def auto_shelf_waiting_for_test_share(
    message: Message,
    state: FSMContext,
    redis_client: RedisClient = Provide["redis_client_wrapper"],
) -> None:
    await _handle_fsm_update(
        message=message,
        state=state,
        redis_client=redis_client,
        update_method="update_test_share",
    )


@router.message(
    StateFilter(states.AutoShelfBidControlFSM.waiting_for_target_test_impressions)
)
@inject
async def auto_shelf_waiting_for_target_test_impressions(
    message: Message,
    state: FSMContext,
    redis_client: RedisClient = Provide["redis_client_wrapper"],
) -> None:
    await _handle_fsm_update(
        message=message,
        state=state,
        redis_client=redis_client,
        update_method="update_target_test_impressions",
    )


@router.message(
    StateFilter(states.AutoShelfBidControlFSM.waiting_for_target_test_observation_minutes)
)
@inject
async def auto_shelf_waiting_for_target_test_observation_minutes(
    message: Message,
    state: FSMContext,
    redis_client: RedisClient = Provide["redis_client_wrapper"],
) -> None:
    await _handle_fsm_update(
        message=message,
        state=state,
        redis_client=redis_client,
        update_method="update_target_test_observation_minutes",
    )


@router.message(StateFilter(states.AutoShelfBidControlFSM.waiting_for_min_bid_distance))
@inject
async def auto_shelf_waiting_for_min_bid_distance(
    message: Message,
    state: FSMContext,
    redis_client: RedisClient = Provide["redis_client_wrapper"],
) -> None:
    await _handle_fsm_update(
        message=message,
        state=state,
        redis_client=redis_client,
        update_method="update_min_bid_distance",
    )


@router.message(
    StateFilter(states.AutoShelfBidControlFSM.waiting_for_retest_interval_days)
)
@inject
async def auto_shelf_waiting_for_retest_interval_days(
    message: Message,
    state: FSMContext,
    redis_client: RedisClient = Provide["redis_client_wrapper"],
) -> None:
    await _handle_fsm_update(
        message=message,
        state=state,
        redis_client=redis_client,
        update_method="update_retest_interval_days",
    )


@router.callback_query(_asb_exhausted_reset_filter)
@inject
async def auto_shelf_exhausted_reset_pause(
    callback: CallbackQuery,
    redis_client: RedisClient = Provide["redis_client_wrapper"],
) -> None:
    """«Сбросить паузу»: clear only our PG block; no forced Auto start."""
    raw = str(callback.data or "")
    try:
        adv_setting_original_id = int(raw.split(":", 1)[1])
    except (IndexError, ValueError):
        message = _tg_message(callback)
        if message:
            await message.answer("Некорректная кнопка сброса паузы.")
        return None
    service = AutoShelfBidControlTelegramService(redis_client=redis_client)
    try:
        cleared = await service.clear_shelf_exhausted_pause(adv_setting_original_id)
    except AutoShelfBidControlTelegramError as exc:
        message = _tg_message(callback)
        if message:
            await message.answer(exc.message)
        return None
    message = _tg_message(callback)
    if message:
        if cleared:
            await message.answer(
                "Снят только блок паузы «нет ставки под план». "
                "Авто запустится, если нет других ограничений."
            )
        else:
            await message.answer("Активного блока паузы полок не найдено.")
    return None
