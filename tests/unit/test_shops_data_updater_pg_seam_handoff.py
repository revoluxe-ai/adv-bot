"""Mock-only handoff proof for shops_data_updater PG seam."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries import shops_data_updater
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _session_cm(session: AsyncSession):
    @asynccontextmanager
    async def cm(read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        yield session

    return cm


async def _close_queued_coroutine(coro: object) -> None:
    """Закрыть queued coroutine, чтобы unit-тест не оставлял dangling awaitable."""
    close = getattr(coro, "close", None)
    if callable(close):
        close()


async def test_quick_update_advs_parent_hands_off_session() -> None:
    """__quick_update_advs opens read-only session and hands it to child helper."""
    session = AsyncMock(spec=AsyncSession)
    sm_mock = MagicMock(side_effect=_session_cm(session))
    wb_api = MagicMock()
    wb_api.wb_cabinet = SimpleNamespace(shop_id="shop-1")
    wb_api.get_advertIds = AsyncMock(return_value=[10, 20])
    updater = ShopDataUpdater(wb_api=wb_api)
    existing_adv = MagicMock()
    existing_adv.adv_id = 20

    with (
        patch.object(shops_data_updater, "sm", sm_mock),
        patch.object(
            shops_data_updater,
            "load_existing_advs_in_session",
            new_callable=AsyncMock,
            return_value=[existing_adv],
        ) as load_mock,
        patch.object(
            updater,
            "_ShopDataUpdater__quick_update_advs_in_db",
            new_callable=AsyncMock,
            return_value=None,
        ) as update_mock,
        patch.object(
            shops_data_updater._coroutine_parallel_run_queue,
            "put",
            new_callable=AsyncMock,
            side_effect=_close_queued_coroutine,
        ) as put_mock,
    ):
        await updater._ShopDataUpdater__quick_update_advs()

    load_mock.assert_awaited_once_with(session, [10, 20])
    assert update_mock.await_count == 1
    assert update_mock.await_args is not None
    assert update_mock.await_args.args[0] == {10}
    assert update_mock.call_count == 2
    assert update_mock.call_args_list[1].args[0] == {20}
    put_mock.assert_awaited_once()
    assert sm_mock.call_args is not None
    assert sm_mock.call_args.kwargs.get("read_only") is True
