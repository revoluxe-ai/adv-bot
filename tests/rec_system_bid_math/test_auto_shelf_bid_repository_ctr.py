"""Unit tests for mode-aware rec bid aggregation in AutoShelfBidRepository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import pytest

import app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository as repository_module
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
    AutoShelfBidRepository,
)


class _FakeResult:
    def __init__(
        self,
        result_rows: list[tuple[object, ...]],
        column_names: tuple[str, ...],
    ) -> None:
        self.result_rows = result_rows
        self.column_names = column_names


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def query(self, query: str, parameters: dict[str, object]) -> _FakeResult:
        self.calls.append((query, parameters))
        mode = parameters.get("mode")
        if "sum(delta_clicks) AS clicks" in query:
            if mode == "main":
                return _FakeResult(
                    [(100, 200.0, 4.0)],
                    ("bid", "impressions", "clicks"),
                )
            if mode is None:
                return _FakeResult(
                    [(130, 50.0, 5.0)],
                    ("bid", "impressions", "clicks"),
                )
            return _FakeResult(
                [(120, 100.0, 10.0)],
                ("bid", "impressions", "clicks"),
            )
        if mode == "main":
            return _FakeResult(
                [
                    (
                        "main-a1",
                        1,
                        datetime(2026, 6, 7, 3, 0),
                        100,
                        700,
                        10,
                        1,
                        0,
                        1.5,
                    ),
                ],
                (
                    "event_id",
                    "version",
                    "bucket_start",
                    "bid_minor",
                    "price_minor",
                    "delta_impressions",
                    "delta_clicks",
                    "delta_orders",
                    "delta_spend",
                ),
            )
        if mode is None:
            return _FakeResult(
                [
                    (
                        "all-a1",
                        1,
                        datetime(2026, 6, 7, 3, 0),
                        130,
                        800,
                        50,
                        5,
                        1,
                        3.5,
                    )
                ],
                (
                    "event_id",
                    "version",
                    "bucket_start",
                    "bid_minor",
                    "price_minor",
                    "delta_impressions",
                    "delta_clicks",
                    "delta_orders",
                    "delta_spend",
                ),
            )
        return _FakeResult(
            [
                (
                    "test-a1",
                    1,
                    datetime(2026, 6, 7, 3, 0),
                    120,
                    800,
                    30,
                    3,
                    1,
                    3.5,
                )
            ],
            (
                "event_id",
                "version",
                "bucket_start",
                "bid_minor",
                "price_minor",
                "delta_impressions",
                "delta_clicks",
                "delta_orders",
                "delta_spend",
            ),
        )


class _FakeAsyncContext:
    def __init__(self, value: object) -> None:
        self._value = value

    async def __aenter__(self) -> object:
        return self._value

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)
        return None


class _BucketRowsClient:
    def __init__(self, result_rows: list[tuple[object, ...]]) -> None:
        self.result_rows = result_rows
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def query(self, query: str, parameters: dict[str, object]) -> _FakeResult:
        self.calls.append((query, parameters))
        return _FakeResult(
            self.result_rows,
            (
                "bucket_start",
                "bid_minor",
                "price_minor",
                "delta_impressions",
            ),
        )


@pytest.mark.asyncio
async def test_fetch_rec_bid_bucket_observations_for_nmid_passes_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient()
    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(client),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidRepository(wb_manager_hub=None)  # type: ignore[arg-type]
    buckets = await repository.fetch_rec_bid_bucket_observations_for_nmid(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert len(buckets) == 1
    assert buckets[0].bid == 100
    assert buckets[0].impressions == 10.0
    assert client.calls
    query, parameters = client.calls[0]
    assert "%(mode)s" in query
    assert parameters == {
        "nmid": 123,
        "mode": "main",
        "date_from": datetime(2026, 6, 7, 0, 0),
        "date_to": datetime(2026, 6, 8, 0, 0),
    }


@pytest.mark.asyncio
async def test_fetch_rec_bid_bucket_observations_for_nmid_all_modes_omits_mode_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient()
    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(client),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidRepository(wb_manager_hub=None)  # type: ignore[arg-type]
    buckets = await repository.fetch_rec_bid_bucket_observations_for_nmid(
        nmid=123,
        mode=None,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert len(buckets) == 1
    assert buckets[0].bid == 130
    assert buckets[0].impressions == 50.0
    assert client.calls
    query, parameters = client.calls[0]
    assert "mode = %(mode)s" not in query
    assert parameters == {
        "nmid": 123,
        "date_from": datetime(2026, 6, 7, 0, 0),
        "date_to": datetime(2026, 6, 8, 0, 0),
    }


@pytest.mark.asyncio
async def test_fetch_rec_bid_ctr_by_bid_for_nmid_passes_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient()
    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(client),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidRepository(wb_manager_hub=None)  # type: ignore[arg-type]
    ctr_by_bid = await repository.fetch_rec_bid_ctr_by_bid_for_nmid(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert ctr_by_bid == {100: 0.02}
    assert client.calls
    query, parameters = client.calls[0]
    assert "%(mode)s" in query
    assert parameters == {
        "nmid": 123,
        "mode": "main",
        "date_from": datetime(2026, 6, 7, 0, 0),
        "date_to": datetime(2026, 6, 8, 0, 0),
    }


@pytest.mark.asyncio
async def test_fetch_rec_bid_ctr_by_bid_for_nmid_all_modes_omits_mode_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient()
    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(client),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidRepository(wb_manager_hub=None)  # type: ignore[arg-type]
    ctr_by_bid = await repository.fetch_rec_bid_ctr_by_bid_for_nmid(
        nmid=123,
        mode=None,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert ctr_by_bid == {130: 0.1}
    assert client.calls
    query, parameters = client.calls[0]
    assert "mode = %(mode)s" not in query
    assert parameters == {
        "nmid": 123,
        "date_from": datetime(2026, 6, 7, 0, 0),
        "date_to": datetime(2026, 6, 8, 0, 0),
    }


def test_build_bid_bucket_observations_from_ch_rows_sums_rows_in_bucket() -> None:
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
        build_bid_bucket_observations_from_ch_rows,
    )

    rows = [
        {
            "event_id": "a",
            "version": 1,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 10,
            "delta_clicks": 1,
            "delta_orders": 0,
            "delta_spend": 1.5,
        },
        {
            "event_id": "a",
            "version": 2,
            "bucket_start": datetime(2026, 6, 7, 3, 0),
            "bid_minor": 100,
            "price_minor": 700,
            "delta_impressions": 11,
            "delta_clicks": 2,
            "delta_orders": 0,
            "delta_spend": 1.7,
        },
    ]

    buckets = build_bid_bucket_observations_from_ch_rows(rows)

    assert len(buckets) == 1
    assert buckets[0].impressions == 21.0
    assert buckets[0].price_minor == 700


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result_rows, expected",
    [
        (
            [
                (datetime(2026, 6, 7, 3, 0), 100, 700, 10),
                (datetime(2026, 6, 7, 3, 0), 100, 700, 11),
            ],
            {
                (100, 700, 21.0),
            },
        ),
        (
            [
                (datetime(2026, 6, 7, 3, 0), 100, 700, 10),
                (datetime(2026, 6, 7, 3, 0), 101, 700, 11),
            ],
            {
                (100, 700, 10.0),
                (101, 700, 11.0),
            },
        ),
        (
            [
                (datetime(2026, 6, 7, 3, 0), 100, 700, 10),
                (datetime(2026, 6, 7, 3, 0), 100, 800, 11),
            ],
            {
                (100, 700, 10.0),
                (100, 800, 11.0),
            },
        ),
    ],
)
async def test_fetch_rec_bid_bucket_observations_for_nmid_groups_full_bucket_context(
    monkeypatch: pytest.MonkeyPatch,
    result_rows: list[tuple[object, ...]],
    expected: set[tuple[int, int | None, float]],
) -> None:
    client = _BucketRowsClient(result_rows)
    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(client),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidRepository(wb_manager_hub=cast(Any, None))
    buckets = await repository.fetch_rec_bid_bucket_observations_for_nmid(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert {
        (bucket.bid, bucket.price_minor, bucket.impressions) for bucket in buckets
    } == expected
