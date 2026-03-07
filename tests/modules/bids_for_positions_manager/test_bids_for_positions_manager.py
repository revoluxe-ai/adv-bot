"""Unit tests for BidsForPositionsManager and BidPositionRow."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.modules.bids_for_positions_manager import BidsForPositionsManager
from app.modules.bids_for_positions_manager.dto import BidPositionRow


@pytest.mark.unit
def test_sort_bids_for_positions():
    """Сортировка ставок по position."""
    manager = BidsForPositionsManager(None)  # type: ignore[arg-type]
    ts = datetime.now()
    bids = {
        "kw1": [
            BidPositionRow("kw1", 3, 100, ts),
            BidPositionRow("kw1", 1, 80, ts),
            BidPositionRow("kw1", 2, 90, ts),
        ],
    }
    result = BidsForPositionsManager._sort_bids_for_positions(bids)
    assert [p.position for p in result["kw1"]] == [1, 2, 3]


@pytest.mark.unit
def test_delete_bad_bids_keeps_single_item():
    """Одна ставка должна оставаться без изменений."""
    ts = datetime.now()
    items = [BidPositionRow("kw1", 1, 100, ts)]
    result = BidsForPositionsManager._delete_bad_bids(items)
    assert len(result) == 1
    assert result[0].position == 1


@pytest.mark.unit
def test_fill_positions_dobivaet_otsutstvuyushchie():
    """Добивка отсутствующих позиций до positions_size."""
    ts = datetime.now()
    items = [
        BidPositionRow("kw1", 1, 100, ts),
        BidPositionRow("kw1", 3, 120, ts),
    ]
    result = BidsForPositionsManager._fill_positions(items, min_bid=50, size=5)
    positions = [p.position for p in result]
    assert positions == [1, 2, 3, 4, 5]


@pytest.mark.unit
def test_fill_positions_odnorodnyj_keyword():
    """Все позиции от одного keyword."""
    ts = datetime.now()
    items = [
        BidPositionRow("kw1", 1, 100, ts),
        BidPositionRow("kw1", 2, 110, ts),
    ]
    result = BidsForPositionsManager._fill_positions(items, min_bid=50, size=4)
    assert all(p.keyword == "kw1" for p in result)
    assert len(result) == 4


@pytest.mark.unit
def test_fill_positions_raises_raznye_kluchi():
    """Assert при смешении keyword."""
    ts = datetime.now()
    items = [
        BidPositionRow("kw1", 1, 100, ts),
        BidPositionRow("kw2", 2, 110, ts),
    ]
    with pytest.raises(AssertionError, match="разных ключей"):
        BidsForPositionsManager._fill_positions(items, min_bid=50, size=5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_bid_positions_normalized_calls_ch_and_returns_normalized():
    """get_bid_positions_normalized вызывает CH и возвращает нормализованные строки без conv."""
    mock_ch = AsyncMock()
    ts = datetime.now()
    mock_ch.get_bids_for_positions = AsyncMock(
        return_value={
            "kw1": [
                BidPositionRow("kw1", 1, 100, ts),
                BidPositionRow("kw1", 2, 110, ts),
            ],
        }
    )
    manager = BidsForPositionsManager(mock_ch)
    result = await manager.get_bid_positions_normalized(
        nmid=12345, min_bid=50, positions_size=5
    )
    mock_ch.get_bids_for_positions.assert_called_once_with(nmid=12345)
    assert "kw1" in result
    # Normalization fills positions and trims; we get list of BidPositionRow
    assert all(isinstance(p, BidPositionRow) for p in result["kw1"])
    assert not hasattr(result["kw1"][0], "conv_carts_to_views") or getattr(
        result["kw1"][0], "conv_carts_to_views", None
    ) is None
