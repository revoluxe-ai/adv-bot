"""Unit-тесты загрузки снимка суммарного расхода."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.client_bot.user_interface.services import total_spend_snapshot as tss


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_total_spend_snapshot_sums_common(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = SimpleNamespace(adv_id=1, search_adv_id=2)
    monkeypatch.setattr(
        tss.full_wb_adv_stat,
        "get_total_spend_by_advs",
        AsyncMock(side_effect=[100.0, 50.0]),
    )
    snap = await tss.load_total_spend_snapshot(adv)  # type: ignore[arg-type]
    assert snap.auto == 100.0
    assert snap.search == 50.0
    assert snap.common == 150.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_total_spend_missing_search_is_zero_without_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = SimpleNamespace(adv_id=1, search_adv_id=None)
    ch_mock = AsyncMock(return_value=10.0)
    monkeypatch.setattr(tss.full_wb_adv_stat, "get_total_spend_by_advs", ch_mock)
    snap = await tss.load_total_spend_snapshot(adv)  # type: ignore[arg-type]
    assert snap.search == 0.0
    ch_mock.assert_awaited_once_with([1])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_total_spend_clickhouse_error_returns_none_leg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = SimpleNamespace(adv_id=1, search_adv_id=2)
    monkeypatch.setattr(
        tss.full_wb_adv_stat,
        "get_total_spend_by_advs",
        AsyncMock(side_effect=[RuntimeError("ch down"), 5.0]),
    )
    snap = await tss.load_total_spend_snapshot(adv)  # type: ignore[arg-type]
    assert snap.auto is None
    assert snap.search == 5.0
    assert snap.common is None
