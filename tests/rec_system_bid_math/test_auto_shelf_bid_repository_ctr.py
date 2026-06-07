"""Unit tests for real CTR aggregation in AutoShelfBidRepository."""

from __future__ import annotations

from datetime import datetime

import pytest

import app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository as repository_module
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
    AutoShelfBidRepository,
)


class _FakeResult:
    def __init__(self, result_rows: list[tuple[object, ...]], column_names: tuple[str, ...]) -> None:
        self.result_rows = result_rows
        self.column_names = column_names


class _FakeClient:
    def __init__(self, result_rows: list[tuple[object, ...]], column_names: tuple[str, ...]) -> None:
        self._result = _FakeResult(result_rows, column_names)

    async def query(self, query: str, parameters: dict[str, object]) -> _FakeResult:
        _ = (query, parameters)
        return self._result


class _FakeAsyncContext:
    def __init__(self, value: object) -> None:
        self._value = value

    async def __aenter__(self) -> object:
        return self._value

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)
        return None


@pytest.mark.asyncio
async def test_fetch_rec_bid_ctr_by_bid_for_nmid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(
            _FakeClient(
                [
                    (100, 200.0, 4.0),
                    (120, 0.0, 0.0),
                ],
                ("bid", "impressions", "clicks"),
            )
        ),
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

    assert ctr_by_bid == {100: 0.02, 120: 0.0}


@pytest.mark.asyncio
async def test_fetch_rec_bid_click_to_order_cr_7d_for_nmid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(
            _FakeClient(
                [(0.25,)],
                ("click_to_order_cr_7d",),
            )
        ),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidRepository(wb_manager_hub=None)  # type: ignore[arg-type]
    value = await repository.fetch_rec_bid_click_to_order_cr_7d_for_nmid(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert value == 0.25


@pytest.mark.asyncio
async def test_fetch_rec_bid_click_to_order_cr_7d_for_nmid_returns_zero_on_no_clicks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "get_clickhouse_client",
        lambda: _FakeAsyncContext(
            _FakeClient(
                [(0.0,)],
                ("click_to_order_cr_7d",),
            )
        ),
    )
    monkeypatch.setattr(
        repository_module,
        "anti_ch_crash_semaphore",
        _FakeAsyncContext(None),
    )

    repository = AutoShelfBidRepository(wb_manager_hub=None)  # type: ignore[arg-type]
    value = await repository.fetch_rec_bid_click_to_order_cr_7d_for_nmid(
        nmid=123,
        mode="main",
        date_from=datetime(2026, 6, 7, 0, 0),
        date_to=datetime(2026, 6, 8, 0, 0),
    )

    assert value == 0.0
