from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .repository import FULL_DAY_MASK, TimeSettingsDbState
from .state import TimeSettingsState, normalize_date_enabled

DAY_NAMES = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
DAY_NAMES_FULL = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]


def count_enabled_hours(state: TimeSettingsState) -> int:
    return sum(len(hours) for hours in state.week.values())


def count_active_days(state: TimeSettingsState) -> int:
    return sum(1 for hours in state.week.values() if hours)


def hour_ranges(hours: set[int]) -> list[tuple[int, int]]:
    if not hours:
        return []
    sorted_hours = sorted(hours)
    ranges: list[tuple[int, int]] = []
    start = sorted_hours[0]
    prev = sorted_hours[0]
    for hour in sorted_hours[1:]:
        if hour == prev + 1:
            prev = hour
            continue
        ranges.append((start, prev + 1))
        start = hour
        prev = hour
    ranges.append((start, prev + 1))
    return ranges


def format_day_summary(hours: set[int]) -> str:
    if not hours:
        return "выключено"
    ranges = hour_ranges(hours)
    if len(ranges) == 1:
        start, end = ranges[0]
        return f"{start:02d}–{end:02d} ({len(hours)}ч)"
    parts = [f"{start:02d}–{end:02d}" for start, end in ranges]
    return f"{', '.join(parts)} ({len(hours)}ч)"


def allowed_now(state: TimeSettingsState) -> bool:
    tz = ZoneInfo(state.timezone)
    now = datetime.now(tz)
    date_today = now.date()

    time_ok = True
    if state.schedule_enabled:
        time_ok = now.hour in state.week[now.weekday()]

    normalize_date_enabled(state)
    date_ok = True
    if state.date_enabled:
        if state.date_start is not None and date_today < state.date_start:
            date_ok = False
        if state.date_end is not None and date_today > state.date_end:
            date_ok = False

    return time_ok and date_ok


def allowed_now_from_db_state(
    db_state: TimeSettingsDbState,
    *,
    now: datetime | None = None,
) -> bool:
    """Проверка «разрешено ли сейчас» по данным из БД (для фоновых сервисов).

    Учитывает расписание по часам/дням недели и период по датам (date_start/
    date_end). Вызывается только из AutoAdvActiveControlService для кампаний
    с включённым «Контролем активности» (auto_budget_watchdog_enabled).
    Другие сервисы (бидер и т.д.) ограничения по времени не проверяют —
    это задумано: применение расписания привязано к механизму контроля активности.
    """
    tz = ZoneInfo(db_state.timezone)
    moment = now if now is not None else datetime.now(tz)
    moment = moment.astimezone(tz)  # расписание и даты в timezone настроек (МСК)
    date_today = moment.date()

    time_ok = True
    if db_state.schedule_enabled:
        dow = moment.weekday()
        # Missing DOW = all hours allowed (match hydrate_state_from_db / TimeSettingsState default)
        mask = db_state.masks_by_dow.get(dow, FULL_DAY_MASK)
        time_ok = (mask & (1 << moment.hour)) != 0

    date_ok = True
    if db_state.date_enabled:
        if db_state.date_start is not None and date_today < db_state.date_start:
            date_ok = False
        if db_state.date_end is not None and date_today > db_state.date_end:
            date_ok = False

    return time_ok and date_ok


def toggle_hour(state: TimeSettingsState, dow: int, hour: int) -> None:
    hours = state.week[dow]
    if hour in hours:
        hours.remove(hour)
    else:
        hours.add(hour)


def set_day(state: TimeSettingsState, dow: int, enabled: bool) -> None:
    state.week[dow] = set(range(24)) if enabled else set()


def set_all_week(state: TimeSettingsState, enabled: bool) -> None:
    for dow in range(7):
        set_day(state, dow, enabled)


def validate_range(start: int, end: int) -> bool:
    return 0 <= start <= 23 and 1 <= end <= 24 and end > start


def apply_range(state: TimeSettingsState, dow: int, start: int, end: int, enabled: bool) -> bool:
    if not validate_range(start, end):
        return False
    hours = state.week[dow]
    for hour in range(start, end):
        if enabled:
            hours.add(hour)
        else:
            hours.discard(hour)
    return True


def apply_preset(state: TimeSettingsState, preset: str) -> None:
    set_all_week(state, enabled=False)
    if preset == "24_7":
        set_all_week(state, enabled=True)
    elif preset == "day_09_21":
        for dow in range(7):
            for hour in range(9, 21):
                state.week[dow].add(hour)
    elif preset == "night_21_09":
        for dow in range(7):
            for hour in range(21, 24):
                state.week[dow].add(hour)
            for hour in range(0, 9):
                state.week[dow].add(hour)
    elif preset == "weekdays_09_21":
        for dow in range(0, 5):
            for hour in range(9, 21):
                state.week[dow].add(hour)
    elif preset == "weekends_10_22":
        for dow in (5, 6):
            for hour in range(10, 22):
                state.week[dow].add(hour)
    state.schedule_enabled = True


def shift_date(base: date, delta_days: int) -> date:
    return base + timedelta(days=delta_days)


def set_date_value(state: TimeSettingsState, mode: str, value: date) -> None:
    if mode == "start":
        state.date_start = value
    if mode == "end":
        state.date_end = value
    state.date_enabled = True


def clear_date_value(state: TimeSettingsState, mode: str) -> None:
    if mode == "start":
        state.date_start = None
    if mode == "end":
        state.date_end = None
    normalize_date_enabled(state)


def copy_day_to_targets(state: TimeSettingsState) -> None:
    source = state.copy_source
    source_hours = set(state.week[source])
    for dow in state.copy_targets:
        if dow == source:
            continue
        state.week[dow] = set(source_hours)


def hours_to_mask(hours: set[int]) -> int:
    mask = 0
    for hour in hours:
        mask |= 1 << hour
    return mask


def week_masks_from_state(state: TimeSettingsState) -> dict[int, int]:
    return {dow: hours_to_mask(hours) for dow, hours in state.week.items()}


def range_to_mask(start: int, end: int) -> int:
    return sum(1 << hour for hour in range(start, end))
