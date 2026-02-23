from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import secrets

from .repository import TimeSettingsDbState


MOSCOW_TZ = "Europe/Moscow"
SESSION_TTL = timedelta(hours=24)


@dataclass
class TimeSettingsState:
    schedule_enabled: bool = False
    date_enabled: bool = False
    date_start: date | None = None
    date_end: date | None = None
    week: dict[int, set[int]] = field(
        default_factory=lambda: {dow: set(range(24)) for dow in range(7)}
    )
    adv_setting_id: int | None = None
    timezone: str = MOSCOW_TZ
    selected_dow: int = 0
    range_start: int = 9
    range_end: int = 21
    datepick_mode: str | None = None
    datepick_cursor: date = field(default_factory=lambda: datetime.now(ZoneInfo(MOSCOW_TZ)).date())
    copy_source: int = 0
    copy_targets: set[int] = field(default_factory=set)
    current_screen: str = "A"


@dataclass
class TimeSettingsSession:
    state: TimeSettingsState
    session_message_id: int
    session_id: str
    updated_at: datetime


SessionKey = tuple[int, int]

_SESSIONS: dict[SessionKey, TimeSettingsSession] = {}
_ADV_LOCKS: dict[int, asyncio.Lock] = {}


def make_session_key(user_id: int, adv_setting_id: int | None) -> SessionKey:
    return (user_id, adv_setting_id or 0)


def _now_moscow() -> datetime:
    return datetime.now(ZoneInfo(MOSCOW_TZ))


def new_session(adv_setting_id: int | None, message_id: int) -> TimeSettingsSession:
    state = TimeSettingsState(adv_setting_id=adv_setting_id)
    return TimeSettingsSession(
        state=state,
        session_message_id=message_id,
        session_id=secrets.token_urlsafe(5),
        updated_at=_now_moscow(),
    )


def get_or_create_session(
    user_id: int,
    adv_setting_id: int | None,
    message_id: int,
) -> TimeSettingsSession:
    key = make_session_key(user_id, adv_setting_id)
    session = _SESSIONS.get(key)
    now = _now_moscow()
    if session is None or now - session.updated_at > SESSION_TTL:
        session = new_session(adv_setting_id=adv_setting_id, message_id=message_id)
        _SESSIONS[key] = session
        return session
    if session.session_message_id != message_id:
        session.session_message_id = message_id
    session.updated_at = now
    return session


def normalize_date_enabled(state: TimeSettingsState) -> None:
    if state.date_start is None and state.date_end is None:
        state.date_enabled = False


def find_session_by_message(user_id: int, message_id: int) -> TimeSettingsSession | None:
    now = _now_moscow()
    for key, session in list(_SESSIONS.items()):
        key_user_id, _ = key
        if key_user_id != user_id:
            continue
        if now - session.updated_at > SESSION_TTL:
            _SESSIONS.pop(key, None)
            continue
        if session.session_message_id == message_id:
            session.updated_at = now
            return session
    return None


def get_adv_lock(adv_setting_id: int) -> asyncio.Lock:
    lock = _ADV_LOCKS.get(adv_setting_id)
    if lock is None:
        lock = asyncio.Lock()
        _ADV_LOCKS[adv_setting_id] = lock
    return lock


def _mask_to_hours(mask: int) -> set[int]:
    return {hour for hour in range(24) if mask & (1 << hour)}


def hydrate_state_from_db(
    adv_setting_id: int,
    db_state: TimeSettingsDbState | None,
) -> TimeSettingsState:
    state = TimeSettingsState(adv_setting_id=adv_setting_id)
    if db_state is None:
        return state
    state.schedule_enabled = db_state.schedule_enabled
    state.date_enabled = db_state.date_enabled
    state.date_start = db_state.date_start
    state.date_end = db_state.date_end
    state.timezone = db_state.timezone
    for dow in range(7):
        if dow in db_state.masks_by_dow:
            state.week[dow] = _mask_to_hours(db_state.masks_by_dow[dow])
    normalize_date_enabled(state)
    return state


def set_session_state(session: TimeSettingsSession, state: TimeSettingsState) -> None:
    current_screen = session.state.current_screen
    selected_dow = session.state.selected_dow
    range_start = session.state.range_start
    range_end = session.state.range_end
    datepick_mode = session.state.datepick_mode
    datepick_cursor = session.state.datepick_cursor
    copy_source = session.state.copy_source
    copy_targets = set(session.state.copy_targets)

    session.state = state
    session.state.current_screen = current_screen
    session.state.selected_dow = selected_dow
    session.state.range_start = range_start
    session.state.range_end = range_end
    session.state.datepick_mode = datepick_mode
    session.state.datepick_cursor = datepick_cursor
    session.state.copy_source = copy_source
    session.state.copy_targets = copy_targets
    session.updated_at = _now_moscow()
