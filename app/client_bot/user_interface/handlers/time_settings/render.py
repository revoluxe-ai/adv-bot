from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.user_interface.views import callbacks as main_callbacks

from .callbacks import TS
from .logic import (
    DAY_NAMES,
    DAY_NAMES_FULL,
    allowed_now,
    count_active_days,
    count_enabled_hours,
    format_day_summary,
)
from .state import TimeSettingsSession, TimeSettingsState, normalize_date_enabled


def _pack(
    sid: str,
    a: str,
    adv: int | None = None,
    dow: int | None = None,
    h: int | None = None,
    v: str | None = None,
) -> str:
    return TS(a=a, adv=adv, dow=dow, h=h, v=v, sid=sid).pack()


def _fmt_date_obj(value) -> str:
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d")


def render_screen(session: TimeSettingsSession) -> tuple[str, InlineKeyboardMarkup]:
    screen = session.state.current_screen
    if screen == "B":
        return render_screen_b(session.state, session.session_id)
    if screen == "C":
        return render_screen_c(session.state, session.session_id)
    if screen == "D":
        return render_screen_d(session.state, session.session_id)
    if screen == "P":
        return render_screen_p(session.state, session.session_id)
    if screen == "COPY":
        return render_screen_copy(session.state, session.session_id)
    if screen == "RANGE":
        return render_screen_range(session.state, session.session_id)
    if screen == "DATEPICK":
        return render_screen_datepick(session.state, session.session_id)
    return render_screen_a(session.state, session.session_id)


def render_screen_a(state: TimeSettingsState, sid: str) -> tuple[str, InlineKeyboardMarkup]:
    normalize_date_enabled(state)
    time_mode = (
        "Отключено (показы в любые часы)"
        if not state.schedule_enabled
        else "Включено (только в выбранные часы)"
    )
    date_mode = "Нет" if not state.date_enabled else "Период"
    allowed_label = "разрешено ✅" if allowed_now(state) else "запрещено ⛔"
    enabled_hours = count_enabled_hours(state)
    active_days = count_active_days(state)
    title = "⏰ Ограничения показов"
    if state.adv_setting_id is None:
        title += " (демо)"
    # Для привязанной к РК сессии напоминаем: ограничения действуют при включённом контроле активности
    apply_note = (
        "\nПрименяются при включённом «Контроле активности кампании»."
        if state.adv_setting_id is not None
        else ""
    )
    text = (
        f"{title}\n"
        f"Ограничение по часам: {time_mode}\n"
        f"По датам: {date_mode}\n"
        "Часовой пояс: Москва\n"
        f"Сейчас: {allowed_label}\n"
        f"Включено часов: {enabled_hours}/168\n"
        f"Активных дней: {active_days}/7"
        f"{apply_note}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗓 Неделя", callback_data=_pack(sid, "to_week")))
    builder.row(InlineKeyboardButton(text="📅 Даты", callback_data=_pack(sid, "to_dates")))
    builder.row(
        InlineKeyboardButton(text="⚡ Пресеты", callback_data=_pack(sid, "to_presets"))
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Включить всё", callback_data=_pack(sid, "week_all_on")
        ),
        InlineKeyboardButton(
            text="⛔ Выключить всё", callback_data=_pack(sid, "week_all_off")
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=(
                "🟢 Включить ограничение по часам"
                if not state.schedule_enabled
                else "⚪ Отключить ограничение по часам"
            ),
            callback_data=_pack(sid, "toggle_schedule"),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"По датам: {'Нет' if not state.date_enabled else 'Период'}",
            callback_data=_pack(sid, "toggle_dates"),
        )
    )
    if state.adv_setting_id is not None:
        builder.row(
            InlineKeyboardButton(
                text="⬅️ К настройкам кампании",
                callback_data=main_callbacks.Adv(
                    adv_original_id=state.adv_setting_id
                ).pack(),
            )
        )
    return text, builder.as_markup()


def render_screen_b(state: TimeSettingsState, sid: str) -> tuple[str, InlineKeyboardMarkup]:
    lines = ["🗓 Расписание по неделе", "Выберите день для редактирования"]
    for dow in range(7):
        lines.append(f"{DAY_NAMES[dow]}: {format_day_summary(state.week[dow])}")
    text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    for dow in range(7):
        builder.add(
            InlineKeyboardButton(
                text=DAY_NAMES[dow],
                callback_data=_pack(sid, "to_day", dow=dow),
            )
        )
    builder.adjust(4, 3)
    builder.row(
        InlineKeyboardButton(
            text="📋 Копировать день",
            callback_data=_pack(sid, "to_copy"),
        )
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=_pack(sid, "back_a")))
    return text, builder.as_markup()


def render_screen_c(state: TimeSettingsState, sid: str) -> tuple[str, InlineKeyboardMarkup]:
    dow = state.selected_dow
    text = (
        f"📆 {DAY_NAMES_FULL[dow]}\n"
        f"Активные часы: {format_day_summary(state.week[dow])}\n"
        "Нажимайте часы, чтобы включать/выключать"
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Включить день", callback_data=_pack(sid, "day_on")),
        InlineKeyboardButton(text="⛔ Выключить день", callback_data=_pack(sid, "day_off")),
    )
    builder.row(
        InlineKeyboardButton(text="➕ Диапазон", callback_data=_pack(sid, "to_range"))
    )
    # Add 24 hour buttons in 4 rows of 6 (adjust() would flatten prior rows too)
    for row_start in range(0, 24, 6):
        hour_buttons = [
            InlineKeyboardButton(
                text=f"{'✓' if hour in state.week[dow] else '·'} {hour:02d}",
                callback_data=_pack(sid, "toggle_hour", dow=dow, h=hour),
            )
            for hour in range(row_start, row_start + 6)
        ]
        builder.row(*hour_buttons)
    builder.row(
        InlineKeyboardButton(
            text="📋 Копировать этот день",
            callback_data=_pack(sid, "copy_from_day", dow=dow),
        )
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=_pack(sid, "back_b")))
    return text, builder.as_markup()


def render_screen_d(state: TimeSettingsState, sid: str) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "📅 Период по датам\n"
        f"Начало: {_fmt_date_obj(state.date_start)}\n"
        f"Конец: {_fmt_date_obj(state.date_end)}\n"
        "Примечание: можно указать только начало или только конец"
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Начало: выбрать",
            callback_data=_pack(sid, "to_datepick", v="start"),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Конец: выбрать",
            callback_data=_pack(sid, "to_datepick", v="end"),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Очистить начало",
            callback_data=_pack(sid, "clear_date", v="start"),
        ),
        InlineKeyboardButton(
            text="Очистить конец",
            callback_data=_pack(sid, "clear_date", v="end"),
        ),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=_pack(sid, "back_a")))
    return text, builder.as_markup()


def render_screen_p(state: TimeSettingsState, sid: str) -> tuple[str, InlineKeyboardMarkup]:
    text = "⚡ Пресеты расписания"
    builder = InlineKeyboardBuilder()
    presets = [
        ("24/7", "24_7"),
        ("День 09–21", "day_09_21"),
        ("Ночь 21–09", "night_21_09"),
        ("Будни 09–21", "weekdays_09_21"),
        ("Выходные 10–22", "weekends_10_22"),
    ]
    for title, code in presets:
        builder.row(
            InlineKeyboardButton(
                text=title,
                callback_data=_pack(sid, "preset", v=code),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=_pack(sid, "back_a")))
    return text, builder.as_markup()


def render_screen_copy(state: TimeSettingsState, sid: str) -> tuple[str, InlineKeyboardMarkup]:
    source = state.copy_source
    targets = sorted(state.copy_targets)
    targets_str = ", ".join(DAY_NAMES[d] for d in targets) if targets else "не выбраны"
    text = (
        "📋 Копирование дня\n"
        f"Источник: {DAY_NAMES[source]}\n"
        f"Назначение: {targets_str}"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Источник", callback_data=_pack(sid, "noop")))
    builder.row(
        *[
            InlineKeyboardButton(
                text=f"{'● ' if dow == source else ''}{DAY_NAMES[dow]}",
                callback_data=_pack(sid, "copy_source", dow=dow),
            )
            for dow in range(7)
        ]
    )
    builder.row(InlineKeyboardButton(text="Назначение", callback_data=_pack(sid, "noop")))
    builder.row(
        *[
            InlineKeyboardButton(
                text=f"{'✓ ' if dow in state.copy_targets else ''}{DAY_NAMES[dow]}",
                callback_data=_pack(sid, "copy_target", dow=dow),
            )
            for dow in range(7)
            if dow != source
        ]
    )
    builder.row(
        InlineKeyboardButton(text="✅ Применить", callback_data=_pack(sid, "copy_apply")),
        InlineKeyboardButton(text="Очистить выбор", callback_data=_pack(sid, "copy_clear")),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=_pack(sid, "back_b")))
    return text, builder.as_markup()


def render_screen_range(state: TimeSettingsState, sid: str) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "⏱ Диапазон часов\n"
        f"🔹 Начало: {state.range_start:02d}\n"
        f"🔸 Конец: {state.range_end:02d}\n"
        "Правило: конец не включается [start, end)"
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Start -1", callback_data=_pack(sid, "range_start_dec")),
        InlineKeyboardButton(text="Start +1", callback_data=_pack(sid, "range_start_inc")),
    )
    builder.row(
        InlineKeyboardButton(text="End -1", callback_data=_pack(sid, "range_end_dec")),
        InlineKeyboardButton(text="End +1", callback_data=_pack(sid, "range_end_inc")),
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Включить диапазон",
            callback_data=_pack(sid, "range_on"),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⛔ Выключить диапазон",
            callback_data=_pack(sid, "range_off"),
        )
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=_pack(sid, "back_c")))
    return text, builder.as_markup()


def render_screen_datepick(state: TimeSettingsState, sid: str) -> tuple[str, InlineKeyboardMarkup]:
    mode = "даты начала" if state.datepick_mode == "start" else "даты окончания"
    selected_value = (
        _fmt_date_obj(state.datepick_cursor) if state.datepick_mode in {"start", "end"} else "—"
    )
    text = (
        f"📅 Выбор {mode}\n"
        "1) Выберите быстрый вариант (Сегодня/Завтра/+7/+30)\n"
        "2) При необходимости подстройте кнопками -1/+1 день\n"
        "3) Нажмите «✅ Установить выбранную дату»\n"
        f"Выбрано сейчас: {selected_value}\n"
        f"Начало: {_fmt_date_obj(state.date_start)}\n"
        f"Конец: {_fmt_date_obj(state.date_end)}"
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Сегодня", callback_data=_pack(sid, "pick_quick", v="today")),
        InlineKeyboardButton(text="Завтра", callback_data=_pack(sid, "pick_quick", v="tomorrow")),
    )
    builder.row(
        InlineKeyboardButton(text="+7 дней", callback_data=_pack(sid, "pick_quick", v="plus7")),
        InlineKeyboardButton(text="+30 дней", callback_data=_pack(sid, "pick_quick", v="plus30")),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ -1 день", callback_data=_pack(sid, "pick_shift", v="-1")),
        InlineKeyboardButton(text="+1 день ➡️", callback_data=_pack(sid, "pick_shift", v="+1")),
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Установить выбранную дату",
            callback_data=_pack(sid, "pick_apply"),
        )
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=_pack(sid, "back_d")))
    return text, builder.as_markup()
