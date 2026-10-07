"""Fixtures for WB Sky MCP PostgreSQL boundary tests (destructive_local)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.modules.wb_sky_mcp.models import McpConnection
from app.utils.db.base import BaseTable as Base

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]


@pytest.fixture(autouse=True)
async def ensure_mcp_connection_table(async_engine: AsyncEngine) -> None:
    """Register ``mcp_connection`` when session bootstrap omitted the model."""
    async with async_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[McpConnection.__table__],
                checkfirst=True,
            )
        )
