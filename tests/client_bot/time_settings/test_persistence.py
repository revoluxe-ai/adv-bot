from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql

from app.client_bot.user_interface.handlers.time_settings.logic import (
    clear_date_value,
    range_to_mask,
)
from app.client_bot.user_interface.handlers.time_settings.repository import (
    TimeSettingsRepository,
)
from app.client_bot.user_interface.handlers.time_settings.state import (
    TimeSettingsState,
    get_adv_lock,
)


def _sql(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


@pytest.mark.asyncio
async def test_patch_toggle_hour_single_statement_upsert() -> None:
    repo = TimeSettingsRepository()
    session = AsyncMock()

    await repo.patch_toggle_hour(
        session=session,
        adv_setting_id=42,
        dow=1,
        hour=13,
        enabled=False,
    )

    assert session.execute.await_count == 1
    sql = _sql(session.execute.await_args.args[0])
    assert "INSERT INTO adv_time_week_mask" in sql
    assert "ON CONFLICT" in sql
    assert "DO UPDATE" in sql


@pytest.mark.asyncio
async def test_patch_range_single_statement_upsert() -> None:
    repo = TimeSettingsRepository()
    session = AsyncMock()

    await repo.patch_range(
        session=session,
        adv_setting_id=42,
        dow=5,
        range_mask=range_to_mask(9, 21),
        enabled=False,
    )

    assert session.execute.await_count == 1
    sql = _sql(session.execute.await_args.args[0])
    assert "INSERT INTO adv_time_week_mask" in sql
    assert "ON CONFLICT" in sql


@pytest.mark.asyncio
async def test_copy_day_updates_only_targets() -> None:
    repo = TimeSettingsRepository()
    session = AsyncMock()

    await repo.patch_copy_day(
        session=session,
        adv_setting_id=7,
        target_dows=[1, 2, 4],
        source_mask=123,
    )

    assert session.execute.await_count == 1
    sql = _sql(session.execute.await_args.args[0])
    assert "INSERT INTO adv_time_week_mask" in sql
    assert "ON CONFLICT" in sql
    assert "DO UPDATE" in sql
    # Only target dows 1, 2, 4 with adv_setting_id=7 and source_mask=123
    assert "(7, 1, 123)" in sql
    assert "(7, 2, 123)" in sql
    assert "(7, 4, 123)" in sql


def test_clear_dates_turns_date_enabled_off_when_both_empty() -> None:
    state = TimeSettingsState()
    state.date_enabled = True
    state.date_start = None
    state.date_end = None

    clear_date_value(state, "start")
    clear_date_value(state, "end")

    assert state.date_enabled is False


def test_adv_lock_is_stable_per_adv_id() -> None:
    lock1 = get_adv_lock(99)
    lock2 = get_adv_lock(99)
    lock3 = get_adv_lock(100)

    assert lock1 is lock2
    assert lock1 is not lock3
