"""Disposable PostgreSQL boundary evidence for campaign-settings-history.

Requires the repository destructive-local gate:
- localhost/127.0.0.1:5433
- test_adv_bot_db
- ALLOW_DESTRUCTIVE_TEST_DB=1
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import app.modules.campaign_settings_history.coordinator as coordinator_module
from app.modules.campaign_settings_history.coordinator import (
    PostgresTransactionCoordinator,
    locked_cabinet_transaction,
)
from app.modules.campaign_settings_history.pg_reader import (
    PostgresCampaignSettingsReader,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]


@pytest.mark.asyncio
async def test_pg_reader_discovers_and_loads_real_settings_rows(
    async_session: AsyncSession,
) -> None:
    """Boundary read: real PG returns production-shaped settings aggregate."""
    cabinet = WBCabinet(
        shop_id=f"history_{uuid.uuid4().hex}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    async_session.add(cabinet)
    await async_session.flush()

    adv = AdvSetting(
        adv_id=uuid.uuid4().int % 1_000_000_000,
        name="history-boundary",
        wb_cabinet_id=cabinet.id,
        active_status="paused",
        bot_active=False,
        nmids=[111, 222],
    )
    async_session.add(adv)
    await async_session.flush()

    reader = PostgresCampaignSettingsReader(async_session)
    discovered = await reader.discover_cabinet_ids()
    batch = await reader.load_cabinet(int(cabinet.id))

    assert int(cabinet.id) in discovered
    assert batch.wb_cabinet_id == int(cabinet.id)
    assert batch.shop_id == cabinet.shop_id
    assert len(batch.campaigns) == 1
    campaign = batch.campaigns[0]
    assert campaign.adv_setting_id == int(adv.id)
    assert campaign.sources.adv_setting["bot_active"] is False
    assert campaign.sources.adv_setting["nmids"] == [111, 222]


@pytest.mark.asyncio
async def test_pg_advisory_xact_lock_serializes_real_sessions(
    async_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boundary other: real PG advisory xact lock allows one cabinet owner."""
    maker = async_sessionmaker(async_engine, expire_on_commit=False)

    @asynccontextmanager
    async def safe_session_maker(*, read_only: bool = False):
        assert read_only is False
        async with maker() as session:
            yield session

    monkeypatch.setattr(
        coordinator_module,
        "get_async_session_maker",
        safe_session_maker,
    )

    lock_key = 20_261_005
    async with locked_cabinet_transaction(lock_key) as first:
        assert first.acquired is True
        first_coordinator = PostgresTransactionCoordinator(first.session)
        assert await first_coordinator.transaction_alive() is True

        async with locked_cabinet_transaction(lock_key) as second:
            assert second.acquired is False

    async with locked_cabinet_transaction(lock_key) as after_release:
        assert after_release.acquired is True
