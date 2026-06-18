"""Тесты изоляции ошибок в ``UpdateClusterBidsManager._apply_command``."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
    DirectEnum,
    NewBid,
    UpdateBidsCommand,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager import (
    UpdateClusterBidsManager,
)
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import (
    BidderKeywordStatus,
)


def _make_manager() -> tuple[UpdateClusterBidsManager, MagicMock, MagicMock, MagicMock]:
    wb_manager = MagicMock()
    wb_manager.set_new_cluster_bids = AsyncMock()
    status_manager = MagicMock()
    status_manager.update_statuses = AsyncMock()
    cluster_bids_manager = MagicMock()
    cluster_bids_manager.remember_bids = AsyncMock()
    manager = UpdateClusterBidsManager(
        wb_manager=wb_manager,
        redis_keyword_bidder_status_manager=status_manager,
        redis_cluster_bids_manager=cluster_bids_manager,
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
    )
    return manager, wb_manager, status_manager, cluster_bids_manager


def _sample_command() -> UpdateBidsCommand:
    return UpdateBidsCommand(
        new_bids=[
            NewBid(
                new_bid=100,
                search_adv_id=1,
                nmid=2,
                cluster="test",
                bidder_keyword_status=BidderKeywordStatus.GOOD,
                step=5,
                direct=DirectEnum.UP,
            )
        ]
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_command_remember_bids_after_statuses_error() -> None:
    """Сбой update_statuses не блокирует remember_bids после успешного WB."""
    manager, wb_manager, status_manager, cluster_bids_manager = _make_manager()
    status_manager.update_statuses.side_effect = RuntimeError("redis statuses down")
    command = _sample_command()

    await manager._apply_command(command)

    wb_manager.set_new_cluster_bids.assert_awaited_once_with(command)
    status_manager.update_statuses.assert_awaited_once_with(command)
    cluster_bids_manager.remember_bids.assert_awaited_once()
    entries = cluster_bids_manager.remember_bids.await_args.args[0]
    assert len(entries) == 1
    assert entries[0].search_adv_id == 1
    assert entries[0].cluster == "test"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_command_propagates_remember_bids_error() -> None:
    """Сбой remember_bids пробрасывается (fail-closed)."""
    manager, wb_manager, status_manager, cluster_bids_manager = _make_manager()
    cluster_bids_manager.remember_bids.side_effect = RuntimeError("redis remember down")
    command = _sample_command()

    with pytest.raises(RuntimeError, match="redis remember down"):
        await manager._apply_command(command)

    wb_manager.set_new_cluster_bids.assert_awaited_once()
    status_manager.update_statuses.assert_awaited_once()
