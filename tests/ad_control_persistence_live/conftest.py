"""
Live PG persistence tests on Alembic-expanded schema (migration-gates job).

Run with::

    pytest tests/ad_control_persistence_live --confcutdir=tests/ad_control_persistence_live

Requires ``AD_CONTROL_PERSISTENCE_PG_URL`` or ``DATABASE_URL`` (sync URL ok).
Schema must already be at repository head (no create_all).
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.migration_ephemeral_baseline import AD_CONTROL_TABLES

_TRUNCATE_SQL = (
    "TRUNCATE adcontrolcampaignfeaturerow, adcontrolshopfeaturerow, "
    "adcontrolslotmutationledger RESTART IDENTITY CASCADE"
)

pytestmark = pytest.mark.integration


def _async_url() -> str:
    raw = os.environ.get("AD_CONTROL_PERSISTENCE_PG_URL") or os.environ.get(
        "DATABASE_URL"
    )
    if not raw:
        pytest.skip("AD_CONTROL_PERSISTENCE_PG_URL or DATABASE_URL required")
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    if raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql+asyncpg://", 1)
    return raw


@pytest.fixture(scope="session")
async def async_engine() -> AsyncEngine:
    engine = create_async_engine(_async_url(), echo=False)
    async with engine.begin() as conn:
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
                pytest.fail(f"missing migrated table: {table}")
    yield engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _truncate_ad_control_tables(async_engine: AsyncEngine) -> None:
    async with async_engine.begin() as conn:
        await conn.execute(text(_TRUNCATE_SQL))
    yield


@pytest.fixture
async def ad_control_session(async_engine: AsyncEngine) -> AsyncSession:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with maker() as session:
        yield session
        await session.rollback()
