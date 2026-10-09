"""Integration fixtures for ad control persistence."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.modules.ad_control_settings.persistence.models import (
    AdControlCampaignFeatureRow,
    AdControlShopFeatureRow,
    AdControlSlotMutationLedger,
)
from app.utils.db.base import Base

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]

_TRUNCATE_SQL = (
    "TRUNCATE adcontrolcampaignfeaturerow, adcontrolshopfeaturerow, "
    "adcontrolslotmutationledger RESTART IDENTITY CASCADE"
)


@pytest.fixture(autouse=True)
async def _ensure_ad_control_tables(async_engine: AsyncEngine) -> None:
    """Create ad control tables if missing (session schema may predate migration)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    AdControlSlotMutationLedger.__table__,
                    AdControlShopFeatureRow.__table__,
                    AdControlCampaignFeatureRow.__table__,
                ],
                checkfirst=True,
            )
        )
        await conn.execute(text(_TRUNCATE_SQL))
    yield


@pytest.fixture
async def ad_control_session(async_engine: AsyncEngine) -> AsyncSession:
    """Committed-capable session (explicit commit in tests)."""
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with maker() as session:
        yield session
        await session.rollback()
