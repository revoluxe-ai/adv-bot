"""Apply integration tests: isolated PG data per test."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.destructive_local

_APPLY_TRUNCATE_SQL = (
    "TRUNCATE wbskyapplyevidence, wbskyapplyattemptrecord, "
    "wbskyapplyidempotencyledger, wbskyapplydryrunreceipt, "
    "wbskycampaignresourceregistry RESTART IDENTITY CASCADE"
)


@pytest.fixture(autouse=True)
async def _reset_apply_pg_data(
    reset_postgres_test_data,  # noqa: ANN001
    async_engine: AsyncEngine,
) -> None:
    """Reset core PG data plus WB Sky registry/apply ledger tables."""
    async with async_engine.begin() as conn:
        await conn.execute(text(_APPLY_TRUNCATE_SQL))
    yield
