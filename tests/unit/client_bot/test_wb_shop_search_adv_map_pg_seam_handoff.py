"""Mock-only handoff proofs for WBShopDataManager search-adv map PG seam."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _session_cm(session: AsyncSession):
    """Build session-maker double that records explicit ``read_only=``."""

    @asynccontextmanager
    async def cm(*, read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        cm.last_read_only = read_only  # type: ignore[attr-defined]
        yield session

    cm.last_read_only = None  # type: ignore[attr-defined]
    return cm


def _manager() -> WBShopDataManager:
    """Minimal manager instance (PG helpers do not use ctor fields)."""
    return WBShopDataManager(
        wb_cabinet=SimpleNamespace(shop_id="shop-x"),  # type: ignore[arg-type]
        tasks_manager=MagicMock(),
        wb_api_data_manager=MagicMock(),
        wb_manager=None,
        plan_fact_reader=MagicMock(),
    )


@pytest.mark.asyncio
async def test_get_adv_id_to_search_adv_map_hands_read_session_to_child() -> None:
    """Parent opens ``sm(read_only=True)`` and delegates to static child."""
    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    expected = {101: SimpleNamespace(adv_id=101)}
    child = AsyncMock(return_value=expected)
    manager = _manager()
    ids = {101, 202}

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.sm",
            sm_cm,
        ),
        patch.object(
            WBShopDataManager,
            "_WBShopDataManager__get_adv_id_to_search_adv_map",
            child,
        ),
    ):
        result = await manager._get_adv_id_to_search_adv_map(ids)

    assert sm_cm.last_read_only is True
    child.assert_awaited_once_with(session, ids)
    assert result is expected
