"""Integration fixtures for ad control persistence (migration-backed schema)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.migration_ephemeral_baseline import AD_CONTROL_TABLES

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]

_TRUNCATE_SQL = (
    "TRUNCATE adcontrolcampaignfeaturerow, adcontrolshopfeaturerow, "
    "adcontrolslotmutationledger RESTART IDENTITY CASCADE"
)


@pytest.fixture(autouse=True)
async def _require_ad_control_tables(async_engine: AsyncEngine) -> None:
    """Fail if session schema lacks migration-created ad-control tables."""
    async with async_engine.begin() as conn:
        for table in AD_CONTROL_TABLES:
            exists = await conn.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = :name
                    )
                    """
                ),
                {"name": table},
            )
            if not exists:
                pytest.fail(
                    f"missing {table}: run test DB bootstrap / Alembic head "
                    "(do not rely on create_all in this package)"
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
