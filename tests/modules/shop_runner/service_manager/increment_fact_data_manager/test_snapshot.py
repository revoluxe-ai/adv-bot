from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from zoneinfo import ZoneInfo

from app.modules.shop_runner.service_manager.increment_fact_data_manager.dto.fact_stat_snapshot import (
    FactStatSnapshot,
)
from app.modules.shop_runner.service_manager.increment_fact_data_manager.last_state_manager import (
    LastStateManager,
)
from app.modules.shop_runner.service_manager.increment_fact_data_manager.fact_stat_repository import (
    FactStatRepository,
)


def create_snapshot(version: int = 1) -> FactStatSnapshot:
    return FactStatSnapshot(
        shop_id=uuid4(),
        complex_adv_id=123,
        bucket_start=datetime(2026, 2, 1, 10, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        src_ts=datetime(2026, 2, 1, 10, 5, tzinfo=ZoneInfo("Europe/Moscow")),
        version=version,
        views_adv_sum=100,
        clicks_adv_sum=10,
        carts_adv_sum=5,
        orders_adv_sum=2,
        spend_adv_sum_rub=500,
        orders_sum_adv_rub=1000,
        open_card_sum=20,
        carts_card_sum=8,
        orders_card_sum=4,
        orders_sum_card_rub=2000,
        buy_outs_sum=3,
    )


def test_snapshot_delta_counts_changes() -> None:
    current = create_snapshot(version=2)
    prev = create_snapshot(version=1)
    delta = current.delta(prev)
    assert delta["views_adv_sum"] == 0
    assert delta["clicks_adv_sum"] == 0
    assert current.delta_nonzero_count(prev) == 0

    current.views_adv_sum += 5
    delta = current.delta(prev)
    assert delta["views_adv_sum"] == 5
    assert current.delta_nonzero_count(prev) == 1


@pytest.mark.asyncio
async def test_last_state_manager_prefers_redis() -> None:
    redis_client = AsyncMock()
    snapshot = create_snapshot()
    redis_client.get.return_value = snapshot.to_redis()
    repository = AsyncMock(spec=FactStatRepository)
    manager = LastStateManager(redis_client, repository)

    prev_snapshot, source = await manager.get(str(snapshot.shop_id), snapshot.complex_adv_id)

    assert source == "redis"
    assert prev_snapshot == snapshot
    repository.fetch_prev_fact_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_last_state_manager_falls_back_to_clickhouse() -> None:
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    snapshot = create_snapshot()
    repository = AsyncMock(spec=FactStatRepository)
    repository.fetch_prev_fact_state.return_value = snapshot
    manager = LastStateManager(redis_client, repository)

    prev_snapshot, source = await manager.get(str(snapshot.shop_id), snapshot.complex_adv_id)

    assert source == "clickhouse"
    assert prev_snapshot == snapshot
    redis_client.set.assert_awaited_once()
    repository.fetch_prev_fact_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_last_state_manager_returns_none() -> None:
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    repository = AsyncMock(spec=FactStatRepository)
    repository.fetch_prev_fact_state.return_value = None
    manager = LastStateManager(redis_client, repository)

    prev_snapshot, source = await manager.get(str(uuid4()), 1)

    assert prev_snapshot is None
    assert source == "none"


@pytest.mark.asyncio
async def test_last_state_manager_persist_updates_store() -> None:
    redis_client = AsyncMock()
    repository = AsyncMock(spec=FactStatRepository)
    snapshot = create_snapshot()
    manager = LastStateManager(redis_client, repository)

    await manager.persist(snapshot)

    redis_client.set.assert_awaited_once()
    repository.upsert_prev_fact_state.assert_awaited_once_with(snapshot)
