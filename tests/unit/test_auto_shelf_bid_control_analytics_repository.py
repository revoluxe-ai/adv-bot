"""Unit-тесты mode-aware rec-bid запросов control analytics repository."""

from __future__ import annotations

from datetime import datetime

import pytest

import app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_analytics_repository as repository_module
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_analytics_repository import (
    AutoShelfBidControlAnalyticsRepository,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_coverage_selector import (
    BidCoverage,
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
        if "minOrNull(bucket_start) AS first_bucket_start" in query or "min(bucket_start) AS first_bucket_start" in query:
            price_minor = parameters.get("price_minor", None)
            if price_minor == 999:
                return _FakeResult([], ("first_bucket_start",))
            if price_minor == 800:
                return _FakeResult([(datetime(2026, 6, 7, 3, 0),)], ("first_bucket_start",))
            if price_minor == 700 and mode == "main":
                return _FakeResult([(datetime(2026, 6, 7, 4, 0),)], ("first_bucket_start",))
            return _FakeResult([(None,)], ("first_bucket_start",))
        if "sum(delta_clicks) AS clicks" in query and "sum(delta_orders) AS orders" not in query:
            if mode == "main":
                return _FakeResult(
                    [(100, 200.0, 4.0)],
                    ("bid", "impressions", "clicks"),
                )
            return _FakeResult(
                [(130, 50.0, 5.0)],
                ("bid", "impressions", "clicks"),
            )
        if "sum(delta_orders) AS orders" in query:
            if mode == "main":
                return _FakeResult(
                    [(0.2, 4.0, 1.0)],
                    ("click_to_order_cr_7d", "clicks", "orders"),
                )
            return _FakeResult(
                [(0.1, 5.0, 0.5)],
                ("click_to_order_cr_7d", "clicks", "orders"),
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


class _FakeAsyncContext:
    def __init__(self, value: object) -> None:
        self._value = value

    async def __aenter__(self) -> object:
        return self._value

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)
        return None


@pytest.mark.asyncio
async def test_rec_bid_queries_without_mode_filter_for_none(
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

    repository = AutoShelfBidControlAnalyticsRepository()
    buckets = await repository.fetch_rec_bid_bucket_observations_for_nmid(
        nmid=123,
        mode=None,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )
    ctr_by_bid = await repository.fetch_rec_bid_ctr_by_bid_for_nmid(
        nmid=123,
        mode=None,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )
    click_to_order_cr_7d = await repository.fetch_rec_bid_click_to_order_cr_7d_for_nmid(
        nmid=123,
        mode=None,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert len(buckets) == 1
    assert buckets[0].bid == 130
    assert ctr_by_bid == {130: 0.1}
    assert click_to_order_cr_7d == 0.1
    assert len(client.calls) == 3
    for query, parameters in client.calls:
        assert "mode = %(mode)s" not in query
        assert parameters == {
            "nmid": 123,
            "date_from": datetime(2026, 6, 7, 0, 0),
            "date_to": datetime(2026, 6, 8, 0, 0),
        }


@pytest.mark.asyncio
async def test_rec_bid_queries_with_mode_filter_for_main(
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

    repository = AutoShelfBidControlAnalyticsRepository()
    buckets = await repository.fetch_rec_bid_bucket_observations_for_nmid(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )
    ctr_by_bid = await repository.fetch_rec_bid_ctr_by_bid_for_nmid(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )
    click_to_order_cr_7d = await repository.fetch_rec_bid_click_to_order_cr_7d_for_nmid(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert len(buckets) == 1
    assert buckets[0].bid == 100
    assert ctr_by_bid == {100: 0.02}
    assert click_to_order_cr_7d == 0.25
    assert len(client.calls) == 3
    for query, parameters in client.calls:
        assert "mode = %(mode)s" in query
        assert parameters == {
            "nmid": 123,
            "mode": "main",
            "date_from": datetime(2026, 6, 7, 0, 0),
            "date_to": datetime(2026, 6, 8, 0, 0),
        }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("clicks", "orders", "expected"),
    [
        (10.0, 3.0, 0.3),
        (10.0, 0.0, 0.0),
        (4.0, 10.0, 1.0),
        (0.0, 5.0, 0.0),
    ],
)
async def test_click_to_order_cr_7d_is_normalized_to_unit_interval(
    monkeypatch: pytest.MonkeyPatch,
    clicks: float,
    orders: float,
    expected: float,
) -> None:
    class _NormalizationClient:
        async def query(self, query: str, parameters: dict[str, object]) -> _FakeResult:
            _ = (query, parameters)
            return _FakeResult(
                [(2.5, clicks, orders)],
                ("click_to_order_cr_7d", "clicks", "orders"),
            )

    client = _NormalizationClient()
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

    repository = AutoShelfBidControlAnalyticsRepository()
    click_to_order_cr_7d = await repository.fetch_rec_bid_click_to_order_cr_7d_for_nmid(
        nmid=123,
        mode=None,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert click_to_order_cr_7d == expected


@pytest.mark.asyncio
async def test_get_bid_coverages_aggregates_impressions_by_bid_minor(
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

    repository = AutoShelfBidControlAnalyticsRepository()
    coverages = await repository.get_bid_coverages(
        nmid=123,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        currency="RUB",
        price_minor=800,
        mode=None,
    )

    assert coverages == []


@pytest.mark.asyncio
async def test_get_bid_coverages_counts_only_valid_full_hour_observations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _CoverageClient:
        async def query(self, query: str, parameters: dict[str, object]) -> _FakeResult:
            _ = parameters
            assert "mode = %(mode)s" not in query
            return _FakeResult(
                [
                    ("a", 1, datetime(2026, 6, 7, 3, 0), 100, 700, 10, 0, 0, 0.0),
                    ("b", 1, datetime(2026, 6, 7, 3, 15), 100, 700, 20, 0, 0, 0.0),
                    ("c", 1, datetime(2026, 6, 7, 3, 30), 100, 700, 30, 0, 0, 0.0),
                    ("d", 1, datetime(2026, 6, 7, 3, 45), 100, 700, 40, 0, 0, 0.0),
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

    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(_CoverageClient()),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidControlAnalyticsRepository()
    coverages = await repository.get_bid_coverages(
        nmid=123,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        currency="RUB",
        price_minor=700,
        mode=None,
    )

    assert coverages == [BidCoverage(bid_minor=100, impressions=100, valid_hours=1)]


@pytest.mark.asyncio
async def test_get_bid_coverages_mixed_bid_hour_does_not_increase_valid_hours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _MixedBidClient:
        async def query(self, query: str, parameters: dict[str, object]) -> _FakeResult:
            _ = (query, parameters)
            return _FakeResult(
                [
                    ("a", 1, datetime(2026, 6, 7, 3, 0), 100, 700, 10, 0, 0, 0.0),
                    ("b", 1, datetime(2026, 6, 7, 3, 15), 100, 700, 20, 0, 0, 0.0),
                    ("c", 1, datetime(2026, 6, 7, 3, 30), 101, 700, 30, 0, 0, 0.0),
                    ("d", 1, datetime(2026, 6, 7, 3, 45), 100, 700, 40, 0, 0, 0.0),
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

    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(_MixedBidClient()),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidControlAnalyticsRepository()
    coverages = await repository.get_bid_coverages(
        nmid=123,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        currency="RUB",
        price_minor=700,
        mode=None,
    )

    assert coverages == []


@pytest.mark.asyncio
async def test_get_bid_coverages_mixed_price_hour_does_not_increase_valid_hours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _MixedPriceClient:
        async def query(self, query: str, parameters: dict[str, object]) -> _FakeResult:
            _ = (query, parameters)
            return _FakeResult(
                [
                    ("a", 1, datetime(2026, 6, 7, 3, 0), 100, None, 10, 0, 0, 0.0),
                    ("b", 1, datetime(2026, 6, 7, 3, 15), 100, 700, 20, 0, 0, 0.0),
                    ("c", 1, datetime(2026, 6, 7, 3, 30), 100, None, 30, 0, 0, 0.0),
                    ("d", 1, datetime(2026, 6, 7, 3, 45), 100, 700, 40, 0, 0, 0.0),
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

    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(_MixedPriceClient()),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidControlAnalyticsRepository()
    coverages = await repository.get_bid_coverages(
        nmid=123,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        currency="RUB",
        price_minor=None,
        mode=None,
    )

    assert coverages == []


@pytest.mark.asyncio
async def test_get_bid_coverages_price_minor_none_filters_only_null_price(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _NullPriceClient:
        async def query(self, query: str, parameters: dict[str, object]) -> _FakeResult:
            _ = (query, parameters)
            return _FakeResult(
                [
                    ("a", 1, datetime(2026, 6, 7, 3, 0), 100, None, 10, 0, 0, 0.0),
                    ("b", 1, datetime(2026, 6, 7, 3, 15), 100, None, 20, 0, 0, 0.0),
                    ("c", 1, datetime(2026, 6, 7, 3, 30), 100, None, 30, 0, 0, 0.0),
                    ("d", 1, datetime(2026, 6, 7, 3, 45), 100, None, 40, 0, 0, 0.0),
                    ("e", 1, datetime(2026, 6, 7, 3, 0), 100, 700, 99, 0, 0, 0.0),
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

    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(_NullPriceClient()),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidControlAnalyticsRepository()
    coverages = await repository.get_bid_coverages(
        nmid=123,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        currency="RUB",
        price_minor=None,
        mode=None,
    )

    assert coverages == [BidCoverage(bid_minor=100, impressions=100, valid_hours=1)]


@pytest.mark.asyncio
async def test_get_bid_coverages_price_minor_value_filters_exact_price(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ConcretePriceClient:
        async def query(self, query: str, parameters: dict[str, object]) -> _FakeResult:
            _ = (query, parameters)
            return _FakeResult(
                [
                    ("a", 1, datetime(2026, 6, 7, 3, 0), 100, 12345, 10, 0, 0, 0.0),
                    ("b", 1, datetime(2026, 6, 7, 3, 15), 100, 12345, 20, 0, 0, 0.0),
                    ("c", 1, datetime(2026, 6, 7, 3, 30), 100, 12345, 30, 0, 0, 0.0),
                    ("d", 1, datetime(2026, 6, 7, 3, 45), 100, 12345, 40, 0, 0, 0.0),
                    ("e", 1, datetime(2026, 6, 7, 4, 0), 100, 99999, 50, 0, 0, 0.0),
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

    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(_ConcretePriceClient()),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidControlAnalyticsRepository()
    coverages = await repository.get_bid_coverages(
        nmid=123,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        currency="RUB",
        price_minor=12345,
        mode=None,
    )

    assert coverages == [BidCoverage(bid_minor=100, impressions=100, valid_hours=1)]


@pytest.mark.asyncio
async def test_get_bid_coverages_mode_none_does_not_inject_mode_param(
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

    repository = AutoShelfBidControlAnalyticsRepository()
    _ = await repository.get_bid_coverages(
        nmid=123,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        currency="RUB",
        price_minor=800,
        mode=None,
    )

    assert len(client.calls) == 1
    query, parameters = client.calls[0]
    assert "mode = %(mode)s" not in query
    assert "currency = %(currency)s" in query
    assert "price_minor = %(price_minor)s" in query
    assert parameters == {
        "nmid": 123,
        "currency": "RUB",
        "date_from": datetime(2026, 6, 7, 0, 0),
        "date_to": datetime(2026, 6, 8, 0, 0),
        "price_minor": 800,
    }


@pytest.mark.asyncio
async def test_get_bid_coverages_mode_main_applies_mode_filter(
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

    repository = AutoShelfBidControlAnalyticsRepository()
    _ = await repository.get_bid_coverages(
        nmid=123,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        currency="RUB",
        price_minor=700,
        mode="main",
    )

    assert len(client.calls) == 1
    query, parameters = client.calls[0]
    assert "mode = %(mode)s" in query
    assert "currency = %(currency)s" in query
    assert "price_minor = %(price_minor)s" in query
    assert parameters == {
        "nmid": 123,
        "currency": "RUB",
        "mode": "main",
        "date_from": datetime(2026, 6, 7, 0, 0),
        "date_to": datetime(2026, 6, 8, 0, 0),
        "price_minor": 700,
    }


@pytest.mark.asyncio
async def test_get_bid_coverages_only_valid_full_hours_contribute_impressions_and_hours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _PartialInvalidClient:
        async def query(self, query: str, parameters: dict[str, object]) -> _FakeResult:
            _ = (query, parameters)
            return _FakeResult(
                [
                    ("a", 1, datetime(2026, 6, 7, 3, 0), 100, 700, 10, 0, 0, 0.0),
                    ("b", 1, datetime(2026, 6, 7, 3, 15), 100, 700, 20, 0, 0, 0.0),
                    ("c", 1, datetime(2026, 6, 7, 3, 30), 100, 700, 30, 0, 0, 0.0),
                    ("d", 1, datetime(2026, 6, 7, 3, 45), 100, 700, 40, 0, 0, 0.0),
                    ("e", 1, datetime(2026, 6, 7, 4, 0), 100, 700, 50, 0, 0, 0.0),
                    ("f", 1, datetime(2026, 6, 7, 4, 15), 100, 700, 60, 0, 0, 0.0),
                    ("g", 1, datetime(2026, 6, 7, 4, 30), 101, 700, 70, 0, 0, 0.0),
                    ("h", 1, datetime(2026, 6, 7, 4, 45), 100, 700, 80, 0, 0, 0.0),
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

    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(_PartialInvalidClient()),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidControlAnalyticsRepository()
    coverages = await repository.get_bid_coverages(
        nmid=123,
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
        currency="RUB",
        price_minor=700,
        mode=None,
    )

    assert coverages == [BidCoverage(bid_minor=100, impressions=100, valid_hours=1)]


@pytest.mark.asyncio
async def test_get_first_available_bid_bucket_start_none_price_scopes_to_null_only(
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

    repository = AutoShelfBidControlAnalyticsRepository()
    result = await repository.get_first_available_bid_bucket_start(
        nmid=123,
        currency="RUB",
        price_minor=None,
        mode=None,
    )

    assert result is None
    query, parameters = client.calls[0]
    assert "price_minor IS NULL" in query
    assert "mode = %(mode)s" not in query
    assert parameters == {"nmid": 123, "currency": "RUB"}


@pytest.mark.asyncio
async def test_get_first_available_bid_bucket_start_concrete_price_and_mode(
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

    repository = AutoShelfBidControlAnalyticsRepository()
    result = await repository.get_first_available_bid_bucket_start(
        nmid=123,
        currency="RUB",
        price_minor=700,
        mode="main",
    )

    assert result == datetime(2026, 6, 7, 4, 0)
    query, parameters = client.calls[0]
    assert "price_minor = %(price_minor)s" in query
    assert "mode = %(mode)s" in query
    assert parameters == {
        "nmid": 123,
        "currency": "RUB",
        "price_minor": 700,
        "mode": "main",
    }


@pytest.mark.asyncio
async def test_get_first_available_bid_bucket_start_no_rows_returns_none(
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

    repository = AutoShelfBidControlAnalyticsRepository()
    result = await repository.get_first_available_bid_bucket_start(
        nmid=123,
        currency="RUB",
        price_minor=999,
        mode=None,
    )

    assert result is None
    query, parameters = client.calls[0]
    assert "minOrNull(bucket_start) AS first_bucket_start" in query
    assert parameters == {"nmid": 123, "currency": "RUB", "price_minor": 999}
