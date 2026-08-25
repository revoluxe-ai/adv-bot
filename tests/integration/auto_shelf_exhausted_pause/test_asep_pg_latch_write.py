"""ASEP PG SoT: latch / clear / epoch / settings via live async_session.

Contract: ``tests/support/contracts/asep_pg_shelf_exhausted_sot.md``
(``asep.pg.shelf_exhausted_sot.v1``).

Evidence class: ``boundary_integration`` (WRITE + PURE_READ / READ_AFTER_WRITE).
Live execution requires ``AUTHORIZE_ONE_LIVE_RUN`` after independent re-audit;
this file is authored under ``destructive_local`` and is not run in close without
that token.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
    AutoShelfBidControlSettings,
    AutoShelfBidControlState,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
    DEFAULT_RETEST_INTERVAL_DAYS,
    AutoShelfBidControlRepository,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]

_NOW = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)
_DUE = _NOW + timedelta(days=7)
_RESOLVE_KIND = "target"
_RESOLVE_VALUE = 250.0


async def _seed_state(
    async_session: AsyncSession,
    *,
    nmid: int,
    active: bool = False,
    notify_sent_at: datetime | None = None,
    epoch_pending: bool = False,
    epoch_start: datetime | None = None,
    resolve_kind: str | None = None,
    resolve_value: float | None = None,
) -> AutoShelfBidControlState:
    """Insert minimal ``AutoShelfBidControlState`` row for PG SoT tests."""
    state = AutoShelfBidControlState(
        nmid=nmid,
        current_mode="test",
        currency="RUB",
        current_cycle_started_at=_NOW,
        shelf_exhausted_pause_active=active,
        shelf_exhausted_paused_at=_NOW - timedelta(days=1) if active else None,
        shelf_exhausted_due_at=_DUE if active else None,
        shelf_exhausted_notify_sent_at=notify_sent_at,
        shelf_exhausted_epoch_pending=epoch_pending,
        shelf_exhausted_epoch_start=epoch_start,
        shelf_exhausted_resolve_cpo_kind=resolve_kind,
        shelf_exhausted_resolve_cpo_value=resolve_value,
    )
    async_session.add(state)
    await async_session.flush()
    return state


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_latch_persists_our_block(async_session: AsyncSession) -> None:
    """Contract latch_write_read WRITE: latch persists active + resolve CPO."""
    nmid = 9_100_000 + (uuid.uuid4().int % 90_000)
    await _seed_state(async_session, nmid=nmid, active=False)
    repo = AutoShelfBidControlRepository()

    latched = await repo.latch_shelf_exhausted_pause_in_session(
        async_session,
        nmid,
        now=_NOW,
        due_at=_DUE,
        resolve_cpo_kind=_RESOLVE_KIND,
        resolve_cpo_value=_RESOLVE_VALUE,
    )
    assert latched is not None
    assert latched.shelf_exhausted_pause_active is True

    row = (
        await async_session.execute(
            select(AutoShelfBidControlState).where(
                AutoShelfBidControlState.nmid == nmid
            )
        )
    ).scalar_one()
    assert row.shelf_exhausted_pause_active is True
    assert row.shelf_exhausted_due_at == _DUE
    assert row.shelf_exhausted_resolve_cpo_kind == _RESOLVE_KIND
    assert float(row.shelf_exhausted_resolve_cpo_value or 0) == _RESOLVE_VALUE


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_get_state_reads_latched_block(async_session: AsyncSession) -> None:
    """Contract latch_write_read PURE_READ via get_state_in_session."""
    nmid = 9_200_000 + (uuid.uuid4().int % 90_000)
    await _seed_state(
        async_session,
        nmid=nmid,
        active=True,
        resolve_kind=_RESOLVE_KIND,
        resolve_value=_RESOLVE_VALUE,
    )
    repo = AutoShelfBidControlRepository()
    loaded = await repo.get_state_in_session(async_session, nmid)
    assert loaded is not None
    assert loaded.shelf_exhausted_pause_active is True
    assert loaded.shelf_exhausted_resolve_cpo_kind == _RESOLVE_KIND


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_latch_then_get_state(async_session: AsyncSession) -> None:
    """Contract latch_write_read READ_AFTER_WRITE."""
    nmid = 9_300_000 + (uuid.uuid4().int % 90_000)
    await _seed_state(async_session, nmid=nmid, active=False)
    repo = AutoShelfBidControlRepository()
    await repo.latch_shelf_exhausted_pause_in_session(
        async_session,
        nmid,
        now=_NOW,
        due_at=_DUE,
        resolve_cpo_kind="max",
        resolve_cpo_value=180.0,
    )
    loaded = await repo.get_state_in_session(async_session, nmid)
    assert loaded is not None
    assert loaded.shelf_exhausted_pause_active is True
    assert loaded.shelf_exhausted_resolve_cpo_kind == "max"
    assert float(loaded.shelf_exhausted_resolve_cpo_value or 0) == 180.0


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_get_state_resolve_cpo_and_active_distinct_from_cost_empty(
    async_session: AsyncSession,
) -> None:
    """Contract reason account: PG stores resolve CPO + active our-block fields."""
    nmid = 9_400_000 + (uuid.uuid4().int % 90_000)
    await _seed_state(
        async_session,
        nmid=nmid,
        active=True,
        resolve_kind="target",
        resolve_value=199.5,
    )
    repo = AutoShelfBidControlRepository()
    loaded = await repo.get_state_in_session(async_session, nmid)
    assert loaded is not None
    assert loaded.shelf_exhausted_pause_active is True
    assert loaded.shelf_exhausted_resolve_cpo_kind == "target"
    assert float(loaded.shelf_exhausted_resolve_cpo_value or 0) == 199.5
    # Distinct from cost/empty-keywords: kind is target|max only (CK).
    assert loaded.shelf_exhausted_resolve_cpo_kind not in {
        "cost_rule_failed",
        "empty_keywords",
    }


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_clear_persists_inactive_and_resets_notify_latch(
    async_session: AsyncSession,
) -> None:
    """Contract clear_write_read WRITE + READ_AFTER_WRITE."""
    nmid = 9_500_000 + (uuid.uuid4().int % 90_000)
    await _seed_state(
        async_session,
        nmid=nmid,
        active=True,
        notify_sent_at=_NOW - timedelta(hours=1),
        resolve_kind="max",
        resolve_value=250.0,
        epoch_start=_NOW - timedelta(days=3),
    )
    repo = AutoShelfBidControlRepository()
    cleared = await repo.clear_shelf_exhausted_pause_in_session(async_session, nmid)
    assert cleared is True

    loaded = await repo.get_state_in_session(async_session, nmid)
    assert loaded is not None
    assert loaded.shelf_exhausted_pause_active is False
    assert loaded.shelf_exhausted_due_at is None
    assert loaded.shelf_exhausted_notify_sent_at is None
    assert loaded.shelf_exhausted_epoch_pending is True
    assert loaded.shelf_exhausted_resolve_cpo_kind == "max"
    assert loaded.shelf_exhausted_epoch_start is not None


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_keep_block_state_persists(async_session: AsyncSession) -> None:
    """Contract keep_block_no_clear: observe without clear keeps active=true."""
    nmid = 9_600_000 + (uuid.uuid4().int % 90_000)
    await _seed_state(
        async_session,
        nmid=nmid,
        active=True,
        resolve_kind="target",
        resolve_value=210.0,
    )
    repo = AutoShelfBidControlRepository()
    loaded = await repo.get_state_in_session(async_session, nmid)
    assert loaded is not None
    assert loaded.shelf_exhausted_pause_active is True
    # Explicit non-clear: do not call clear_*; re-read still active.
    again = await repo.get_state_in_session(async_session, nmid)
    assert again is not None
    assert again.shelf_exhausted_pause_active is True


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_mark_epoch_started_persists(async_session: AsyncSession) -> None:
    """Contract epoch_write_read WRITE + READ_AFTER_WRITE."""
    nmid = 9_700_000 + (uuid.uuid4().int % 90_000)
    await _seed_state(
        async_session,
        nmid=nmid,
        active=False,
        epoch_pending=True,
    )
    repo = AutoShelfBidControlRepository()
    epoch = _NOW
    updated = await repo.mark_shelf_exhausted_epoch_started_in_session(
        async_session,
        nmid,
        epoch_start=epoch,
    )
    assert updated is not None
    loaded = await repo.get_state_in_session(async_session, nmid)
    assert loaded is not None
    assert loaded.shelf_exhausted_epoch_start == epoch
    assert loaded.shelf_exhausted_epoch_pending is False


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_settings_default_retest_interval_days_is_seven(
    async_session: AsyncSession,
) -> None:
    """Contract default_retest_interval_settings: create default → days == 7."""
    nmid = 9_800_000 + (uuid.uuid4().int % 90_000)
    repo = AutoShelfBidControlRepository()
    settings = await repo.get_or_create_settings_in_session(
        async_session,
        nmid,
        default_max_bid_minor=50_000,
    )
    assert int(settings.retest_interval_days) == DEFAULT_RETEST_INTERVAL_DAYS
    assert int(settings.retest_interval_days) == 7

    reread = (
        await async_session.execute(
            select(AutoShelfBidControlSettings).where(
                AutoShelfBidControlSettings.nmid == nmid
            )
        )
    ).scalar_one()
    assert int(reread.retest_interval_days) == 7
