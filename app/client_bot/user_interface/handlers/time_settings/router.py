"""Обработчики настроек ограничений показов по времени (расписание, даты).

Пользователь настраивает часы/дни недели и период по датам; данные сохраняются
в БД (AdvTimeSettings, AdvTimeWeekMask). Применяются эти настройки только
в AutoAdvActiveControlService при включённом «Контроле активности кампании»
(auto_budget_watchdog_enabled). Кнопка в меню РК показывается всем — это
задумано: можно настроить расписание заранее, оно начнёт действовать после
включения контроля активности.

Callback ACK здесь отдаёт централизованный `CallbackAnswerMiddleware` из
`global_router`. Локальные `callback.answer()` не нужны.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from .callbacks import TS
from .logic import (
    apply_preset,
    apply_range,
    count_enabled_hours,
    clear_date_value,
    copy_day_to_targets,
    hours_to_mask,
    range_to_mask,
    set_all_week,
    set_date_value,
    set_day,
    shift_date,
    toggle_hour,
    validate_range,
    week_masks_from_state,
)
from .repository import TimeSettingsRepository
from .render import render_screen
from .state import (
    MOSCOW_TZ,
    find_session_by_message,
    get_adv_lock,
    get_or_create_session,
    hydrate_state_from_db,
    normalize_date_enabled,
    set_session_state,
)
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()
repo = TimeSettingsRepository()


async def _safe_edit_reply_markup(callback: CallbackQuery, keyboard) -> bool:
    if callback.message is None:
        return False
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        return True
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return False
        raise


async def _edit_message_content(
    callback: CallbackQuery,
    text: str,
    keyboard,
) -> bool:
    if callback.message is None:
        return False
    try:
        if callback.message.text is not None:
            await callback.message.edit_text(text=text, reply_markup=keyboard)
            return True
        await callback.message.edit_caption(caption=text, reply_markup=keyboard)
        return True
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return False
        raise


async def _reload_state_from_db(
    session: AsyncSession,
    callback: CallbackQuery,
    adv_setting_id: int,
) -> None:
    session_state = find_session_by_message(callback.from_user.id, callback.message.message_id)
    if session_state is None:
        return
    db_state = await repo.load_for_adv(session, adv_setting_id=adv_setting_id)
    set_session_state(session_state, hydrate_state_from_db(adv_setting_id, db_state))


async def _apply_db_patch(
    session: AsyncSession,
    action: str,
    callback_data: TS,
    state,
) -> None:
    adv_setting_id = state.adv_setting_id
    if adv_setting_id is None:
        return

    if action == "toggle_schedule":
        if state.schedule_enabled:
            await repo.patch_week_masks(
                session=session,
                adv_setting_id=adv_setting_id,
                masks_by_dow=week_masks_from_state(state),
            )
        await repo.patch_schedule_enabled(
            session=session,
            adv_setting_id=adv_setting_id,
            enabled=state.schedule_enabled,
        )
    elif action == "toggle_dates":
        await repo.patch_date_enabled(
            session=session,
            adv_setting_id=adv_setting_id,
            enabled=state.date_enabled,
        )
    elif action in {"week_all_on", "week_all_off"}:
        await repo.patch_week_masks(
            session=session,
            adv_setting_id=adv_setting_id,
            masks_by_dow=week_masks_from_state(state),
        )
        await repo.patch_schedule_enabled(
            session=session,
            adv_setting_id=adv_setting_id,
            enabled=state.schedule_enabled,
        )
    elif action == "toggle_hour":
        if callback_data.h is not None:
            await repo.patch_toggle_hour(
                session=session,
                adv_setting_id=adv_setting_id,
                dow=state.selected_dow,
                hour=callback_data.h,
                enabled=callback_data.h in state.week[state.selected_dow],
            )
    elif action in {"day_on", "day_off"}:
        await repo.patch_day_mask(
            session=session,
            adv_setting_id=adv_setting_id,
            dow=state.selected_dow,
            mask=hours_to_mask(state.week[state.selected_dow]),
        )
    elif action in {"range_on", "range_off"}:
        await repo.patch_range(
            session=session,
            adv_setting_id=adv_setting_id,
            dow=state.selected_dow,
            range_mask=range_to_mask(state.range_start, state.range_end),
            enabled=action == "range_on",
        )
    elif action == "preset":
        await repo.patch_week_masks(
            session=session,
            adv_setting_id=adv_setting_id,
            masks_by_dow=week_masks_from_state(state),
        )
        await repo.patch_schedule_enabled(
            session=session,
            adv_setting_id=adv_setting_id,
            enabled=True,
        )
    elif action == "copy_apply":
        source_mask = hours_to_mask(state.week[state.copy_source])
        targets = [dow for dow in state.copy_targets if dow != state.copy_source]
        await repo.patch_copy_day(
            session=session,
            adv_setting_id=adv_setting_id,
            target_dows=targets,
            source_mask=source_mask,
        )
    elif action in {"pick_apply", "clear_date"}:
        if state.date_start is not None and state.date_end is not None and state.date_start > state.date_end:
            raise ValueError("Дата начала не может быть позже даты конца")
        await repo.patch_dates(
            session=session,
            adv_setting_id=adv_setting_id,
            date_start=state.date_start,
            date_end=state.date_end,
            date_enabled=state.date_enabled,
        )


async def _redraw(callback: CallbackQuery, only_markup: bool, alert: str | None = None) -> None:
    if callback.message is None:
        return
    session = find_session_by_message(callback.from_user.id, callback.message.message_id)
    if session is None:
        return
    text, keyboard = render_screen(session)
    if only_markup:
        await _safe_edit_reply_markup(callback, keyboard=keyboard)
    else:
        await _edit_message_content(callback, text=text, keyboard=keyboard)
    return


@router.message(Command("time_settings"))
async def time_settings_demo(message: Message) -> None:
    if message.from_user is None:
        return
    session = get_or_create_session(
        user_id=message.from_user.id,
        adv_setting_id=None,
        message_id=message.message_id,
    )
    session.state.current_screen = "A"
    text, keyboard = render_screen(session)
    sent = await message.answer(text, reply_markup=keyboard)
    get_or_create_session(
        user_id=message.from_user.id,
        adv_setting_id=None,
        message_id=sent.message_id,
    )


@router.callback_query(TS.filter())
async def time_settings_callback(
    callback: CallbackQuery,
    callback_data: TS,
) -> None:
    """Обрабатывает callback-события экрана настроек времени.

    Ответ на callback даёт централизованный middleware в `global_router`.
    """
    if callback.from_user is None or callback.message is None:
        return

    action = callback_data.a
    if action == "open":
        session = get_or_create_session(
            user_id=callback.from_user.id,
            adv_setting_id=callback_data.adv,
            message_id=callback.message.message_id,
        )
        if callback_data.adv is not None:
            lock = get_adv_lock(callback_data.adv)
            async with lock:
                async with sm(read_only=False) as db_session:
                    db_state = await repo.load_for_adv(
                        db_session,
                        adv_setting_id=callback_data.adv,
                    )
                    set_session_state(
                        session,
                        hydrate_state_from_db(callback_data.adv, db_state),
                    )
        session.state.current_screen = "A"
        text, keyboard = render_screen(session)
        await _edit_message_content(callback, text=text, keyboard=keyboard)
        return

    session = find_session_by_message(callback.from_user.id, callback.message.message_id)
    if session is None:
        return
    if callback_data.sid and callback_data.sid != session.session_id:
        return

    state = session.state
    only_markup = False
    alert: str | None = None

    if action == "noop":
        return
    if action == "to_week":
        state.current_screen = "B"
    elif action == "to_day":
        state.selected_dow = (
            callback_data.dow if callback_data.dow is not None else 0
        )
        state.current_screen = "C"
    elif action == "to_dates":
        state.current_screen = "D"
    elif action == "to_presets":
        state.current_screen = "P"
    elif action == "to_copy":
        state.current_screen = "COPY"
    elif action == "copy_from_day":
        state.copy_source = (
            callback_data.dow if callback_data.dow is not None else state.selected_dow
        )
        state.copy_targets = set()
        state.current_screen = "COPY"
    elif action == "to_range":
        state.current_screen = "RANGE"
    elif action == "to_datepick":
        state.datepick_mode = callback_data.v
        state.datepick_cursor = (
            state.date_start
            if callback_data.v == "start" and state.date_start
            else state.date_end
            if callback_data.v == "end" and state.date_end
            else datetime.now(ZoneInfo(MOSCOW_TZ)).date()
        )
        state.current_screen = "DATEPICK"
    elif action == "back_a":
        state.current_screen = "A"
    elif action == "back_b":
        state.current_screen = "B"
    elif action == "back_c":
        state.current_screen = "C"
    elif action == "back_d":
        state.current_screen = "D"
    elif action == "toggle_schedule":
        state.schedule_enabled = not state.schedule_enabled
        state.current_screen = "A"
    elif action == "toggle_dates":
        state.date_enabled = not state.date_enabled
        if state.date_enabled:
            if state.date_start is None and state.date_end is None:
                alert = "Фильтр по датам включен. Укажите период"
                state.current_screen = "D"
            else:
                alert = "Фильтр по датам включен"
                state.current_screen = "A"
        else:
            alert = "Фильтр по датам отключен"
            state.current_screen = "A"
    elif action == "week_all_on":
        before = count_enabled_hours(state)
        set_all_week(state, enabled=True)
        state.schedule_enabled = True
        after = count_enabled_hours(state)
        alert = "Уже включено" if before == after else "Включены все часы (по расписанию)"
        state.current_screen = "A"
    elif action == "week_all_off":
        before = count_enabled_hours(state)
        set_all_week(state, enabled=False)
        state.schedule_enabled = True
        after = count_enabled_hours(state)
        alert = "Уже выключено" if before == after else "Выключены все часы (по расписанию)"
        state.current_screen = "A"
    elif action == "toggle_hour":
        if callback_data.dow is not None:
            state.selected_dow = callback_data.dow
        if callback_data.h is not None:
            toggle_hour(state, state.selected_dow, callback_data.h)
            state.current_screen = "C"
    elif action == "day_on":
        set_day(state, state.selected_dow, enabled=True)
        state.current_screen = "C"
    elif action == "day_off":
        set_day(state, state.selected_dow, enabled=False)
        state.current_screen = "C"
    elif action == "range_start_dec":
        candidate = max(0, state.range_start - 1)
        if validate_range(candidate, state.range_end):
            state.range_start = candidate
        else:
            alert = "End должен быть больше Start"
        state.current_screen = "RANGE"
    elif action == "range_start_inc":
        candidate = min(23, state.range_start + 1)
        if validate_range(candidate, state.range_end):
            state.range_start = candidate
        else:
            alert = "End должен быть больше Start"
        state.current_screen = "RANGE"
    elif action == "range_end_dec":
        candidate = max(1, state.range_end - 1)
        if validate_range(state.range_start, candidate):
            state.range_end = candidate
        else:
            alert = "End должен быть больше Start"
        state.current_screen = "RANGE"
    elif action == "range_end_inc":
        candidate = min(24, state.range_end + 1)
        if validate_range(state.range_start, candidate):
            state.range_end = candidate
        else:
            alert = "End должен быть больше Start"
        state.current_screen = "RANGE"
    elif action == "range_on":
        if not apply_range(
            state, state.selected_dow, state.range_start, state.range_end, enabled=True
        ):
            alert = "Некорректный диапазон"
        state.current_screen = "C"
    elif action == "range_off":
        if not apply_range(
            state, state.selected_dow, state.range_start, state.range_end, enabled=False
        ):
            alert = "Некорректный диапазон"
        state.current_screen = "C"
    elif action == "preset":
        if callback_data.v is not None:
            apply_preset(state, callback_data.v)
        state.current_screen = "A"
    elif action == "copy_source":
        if callback_data.dow is not None:
            state.copy_source = callback_data.dow
            state.copy_targets = {d for d in state.copy_targets if d != state.copy_source}
        state.current_screen = "COPY"
    elif action == "copy_target":
        if callback_data.dow is not None and callback_data.dow != state.copy_source:
            if callback_data.dow in state.copy_targets:
                state.copy_targets.remove(callback_data.dow)
            else:
                state.copy_targets.add(callback_data.dow)
        state.current_screen = "COPY"
    elif action == "copy_apply":
        copy_day_to_targets(state)
        state.current_screen = "B"
    elif action == "copy_clear":
        state.copy_targets = set()
        state.current_screen = "COPY"
    elif action == "pick_quick":
        now_date = datetime.now(ZoneInfo(MOSCOW_TZ)).date()
        value = callback_data.v
        if value == "today":
            state.datepick_cursor = now_date
        elif value == "tomorrow":
            state.datepick_cursor = shift_date(now_date, 1)
        elif value == "plus7":
            state.datepick_cursor = shift_date(now_date, 7)
        elif value == "plus30":
            state.datepick_cursor = shift_date(now_date, 30)
        state.current_screen = "DATEPICK"
    elif action == "pick_shift":
        delta = int(callback_data.v or "0")
        state.datepick_cursor = shift_date(state.datepick_cursor, delta)
        state.current_screen = "DATEPICK"
    elif action == "pick_apply":
        mode = state.datepick_mode
        if mode in ("start", "end"):
            set_date_value(state, mode, state.datepick_cursor)
        state.current_screen = "D"
    elif action == "clear_date":
        mode = callback_data.v or ""
        if mode in ("start", "end"):
            clear_date_value(state, mode)
        state.current_screen = "D"
    elif action == "done":
        return

    mutating_actions = {
        "toggle_schedule",
        "toggle_dates",
        "week_all_on",
        "week_all_off",
        "toggle_hour",
        "day_on",
        "day_off",
        "range_on",
        "range_off",
        "preset",
        "copy_apply",
        "pick_apply",
        "clear_date",
    }
    if state.adv_setting_id is not None and action in mutating_actions:
        lock = get_adv_lock(state.adv_setting_id)
        async with lock:
            async with sm(read_only=False) as db_session:
                try:
                    await _apply_db_patch(
                        session=db_session,
                        action=action,
                        callback_data=callback_data,
                        state=state,
                    )
                    await db_session.commit()
                except Exception:
                    await db_session.rollback()
                    await _reload_state_from_db(
                        session=db_session,
                        callback=callback,
                        adv_setting_id=state.adv_setting_id,
                    )
                    await _redraw(
                        callback,
                        only_markup=False,
                        alert="Не удалось сохранить, попробуйте ещё раз",
                    )
                    return

    await _redraw(callback, only_markup=only_markup, alert=alert)
