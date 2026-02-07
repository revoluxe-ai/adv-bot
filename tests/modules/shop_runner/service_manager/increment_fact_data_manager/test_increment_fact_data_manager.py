from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock

from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.increment_fact_data_manager import (
    IncrementFactDataManager,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.bucket_calculator import (
    BucketCalculator,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.dto.fact_stat_row import (
    FactStatRow,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.dto.fact_stat_snapshot import (
    FactStatSnapshot,
)


class FakeRedisClient:
    def __init__(self, data: dict[str, str | None] | None = None) -> None:
        self.data = data or {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> bool:
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    async def eval(self, script: str, num_keys: int, key: str, value: str) -> int:
        stored = self.data.get(key)
        if stored == value:
            del self.data[key]
            return 1
        return 0


class FakeRepository:
    def __init__(self) -> None:
        self.fetch_current_snapshot = AsyncMock()
        self.fetch_prev_fact_state = AsyncMock()
        self.has_zero_interval_record = AsyncMock()
        self.upsert_prev_fact_state = AsyncMock()


class FakeComplexAdv:
    def __init__(self, shop_id: str, adv_id: int) -> None:
        self.shop_id = shop_id
        self.adv_id = adv_id
        self.nmids = []
        self._adv_ids = {adv_id}

    @property
    def all_adv_ids(self) -> set[int]:
        return self._adv_ids


def _make_snapshot(
    shop_id: UUID,
    complex_adv_id: int,
    src_ts: datetime,
    *,
    metrics: dict[str, int] | None = None,
) -> FactStatSnapshot:
    defaults = {
        "views_adv_sum": 0,
        "clicks_adv_sum": 0,
        "carts_adv_sum": 0,
        "orders_adv_sum": 0,
        "spend_adv_sum_rub": 0,
        "orders_sum_adv_rub": 0,
        "open_card_sum": 0,
        "carts_card_sum": 0,
        "orders_card_sum": 0,
        "orders_sum_card_rub": 0,
        "buy_outs_sum": 0,
    }
    if metrics:
        defaults.update(metrics)
    return FactStatSnapshot(
        shop_id=shop_id,
        complex_adv_id=complex_adv_id,
        bucket_start=src_ts,
        src_ts=src_ts,
        version=1,
        **defaults,
    )


def _setup_manager(
    redis_client: FakeRedisClient, repository: FakeRepository
) -> IncrementFactDataManager:
    writer = AsyncMock()
    return IncrementFactDataManager(
        redis_client=redis_client,
        stat_repository=repository,
        writer=writer,
        bucket_calculator=BucketCalculator(),
    )


@pytest.mark.asyncio
async def test_zero_interval_inserted_when_missing() -> None:
    shop_uuid = uuid4()
    complex_adv_id = 11
    now = datetime.now(ZoneInfo("Europe/Moscow")).replace(hour=1, minute=0, second=0, microsecond=0)
    current_snapshot = _make_snapshot(
        shop_uuid,
        complex_adv_id,
        now,
        metrics={
            "views_adv_sum": 5,
            "clicks_adv_sum": 2,
            "carts_adv_sum": 1,
            "orders_adv_sum": 1,
            "spend_adv_sum_rub": 100,
            "orders_sum_adv_rub": 100,
            "open_card_sum": 2,
            "carts_card_sum": 1,
            "orders_card_sum": 1,
            "orders_sum_card_rub": 80,
            "buy_outs_sum": 0,
        },
    )
    prev_snapshot = _make_snapshot(
        shop_uuid,
        complex_adv_id,
        now - timedelta(days=1),
    )

    redis_client = FakeRedisClient()
    repository = FakeRepository()
    repository.fetch_current_snapshot.return_value = current_snapshot
    repository.fetch_prev_fact_state.return_value = prev_snapshot
    repository.has_zero_interval_record.return_value = False

    manager = _setup_manager(redis_client, repository)
    complex_adv = FakeComplexAdv(str(shop_uuid), complex_adv_id)

    await manager.update(complex_adv)

    writer = manager._writer
    bucket_start = datetime(
        now.year, now.month, now.day, 0, 0, 0, tzinfo=ZoneInfo("Europe/Moscow")
    )
    expected_row = FactStatRow(
        bucket_start=bucket_start,
        shop_id=shop_uuid,
        complex_adv_id=complex_adv_id,
        views_adv_sum=current_snapshot.views_adv_sum,
        clicks_adv_sum=current_snapshot.clicks_adv_sum,
        carts_adv_sum=current_snapshot.carts_adv_sum,
        orders_adv_sum=current_snapshot.orders_adv_sum,
        spend_adv_sum_rub=current_snapshot.spend_adv_sum_rub,
        orders_sum_adv_rub=current_snapshot.orders_sum_adv_rub,
        open_card_sum=current_snapshot.open_card_sum,
        carts_card_sum=current_snapshot.carts_card_sum,
        orders_card_sum=current_snapshot.orders_card_sum,
        orders_sum_card_rub=current_snapshot.orders_sum_card_rub,
        buy_outs_sum=current_snapshot.buy_outs_sum,
        src_ts=current_snapshot.src_ts,
        version=current_snapshot.version,
        event_date=current_snapshot.src_ts.date(),
        event_id=current_snapshot.event_id,
    )

    writer.insert.assert_awaited_once_with(expected_row)
    repository.has_zero_interval_record.assert_awaited_once_with(
        shop_uuid, complex_adv_id, bucket_start
    )
    current_date = now.date()
    zero_key = f"zero:fact:{shop_uuid}:{complex_adv_id}:{current_date.isoformat()}"
    assert redis_client.data.get(zero_key) == "1"


@pytest.mark.asyncio
async def test_zero_interval_skipped_when_redis_has_key() -> None:
    shop_uuid = uuid4()
    complex_adv_id = 22
    now = datetime.now(ZoneInfo("Europe/Moscow")).replace(hour=2, minute=0, second=0, microsecond=0)
    current_snapshot = _make_snapshot(shop_uuid, complex_adv_id, now)
    prev_snapshot = _make_snapshot(shop_uuid, complex_adv_id, now - timedelta(days=1))

    current_date = now.date()
    zero_key = f"zero:fact:{shop_uuid}:{complex_adv_id}:{current_date.isoformat()}"
    redis_client = FakeRedisClient({zero_key: "1"})
    repository = FakeRepository()
    repository.fetch_current_snapshot.return_value = current_snapshot
    repository.fetch_prev_fact_state.return_value = prev_snapshot

    manager = _setup_manager(redis_client, repository)
    complex_adv = FakeComplexAdv(str(shop_uuid), complex_adv_id)

    await manager.update(complex_adv)

    writer = manager._writer
    writer.insert.assert_not_awaited()
    repository.has_zero_interval_record.assert_not_awaited()


@pytest.mark.asyncio
async def test_zero_interval_skipped_when_ch_has_record() -> None:
    shop_uuid = uuid4()
    complex_adv_id = 33
    now = datetime.now(ZoneInfo("Europe/Moscow")).replace(hour=3, minute=0, second=0, microsecond=0)
    current_snapshot = _make_snapshot(shop_uuid, complex_adv_id, now)
    prev_snapshot = _make_snapshot(shop_uuid, complex_adv_id, now - timedelta(days=1))

    redis_client = FakeRedisClient()
    repository = FakeRepository()
    repository.fetch_current_snapshot.return_value = current_snapshot
    repository.fetch_prev_fact_state.return_value = prev_snapshot
    repository.has_zero_interval_record.return_value = True

    manager = _setup_manager(redis_client, repository)
    complex_adv = FakeComplexAdv(str(shop_uuid), complex_adv_id)

    await manager.update(complex_adv)

    writer = manager._writer
    writer.insert.assert_not_awaited()
    current_date = now.date()
    zero_key = f"zero:fact:{shop_uuid}:{complex_adv_id}:{current_date.isoformat()}"
    assert redis_client.data.get(zero_key) == "1"
    bucket_start = datetime(
        current_date.year, current_date.month, current_date.day, 0, 0, 0, tzinfo=ZoneInfo("Europe/Moscow")
    )
    repository.has_zero_interval_record.assert_awaited_once_with(
        shop_uuid, complex_adv_id, bucket_start
    )
