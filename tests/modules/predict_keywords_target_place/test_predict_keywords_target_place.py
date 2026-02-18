"""Unit-тесты для PredictKeywordsTargetPlace."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.modules.predict_keywords_target_place.clickhouse_manager.dto import (
    BidPosition,
    ConvCartToViewsOnPosition,
)
from app.modules.predict_keywords_target_place.predict_keywords_target_place import (
    PredictKeywordsTargetPlace,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_target_position_calls_ch_manager():
    """Проверяем, что get_conv_cart_to_views и get_bids_for_positions вызываются с nmid."""
    mock_ch = AsyncMock()
    mock_ch.get_conv_cart_to_views = AsyncMock(return_value={})
    mock_ch.get_bids_for_positions = AsyncMock(return_value={})

    predictor = PredictKeywordsTargetPlace(mock_ch)
    result = await predictor.get_keywords_target_position(
        nmid=12345, min_bid=50, positions_size=10
    )

    mock_ch.get_conv_cart_to_views.assert_called_once_with(nmid=12345, positions_size=10)
    mock_ch.get_bids_for_positions.assert_called_once_with(nmid=12345)
    assert result == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_target_position_returns_empty_when_empty_data():
    """При пустых convs и bids возвращается пустой словарь."""
    mock_ch = AsyncMock()
    mock_ch.get_conv_cart_to_views = AsyncMock(return_value={})
    mock_ch.get_bids_for_positions = AsyncMock(return_value={})

    predictor = PredictKeywordsTargetPlace(mock_ch)
    result = await predictor.get_keywords_target_position(
        nmid=12345, min_bid=50, positions_size=10
    )

    assert result == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_target_position_returns_best_position_when_valid_data():
    """При валидных convs и bids возвращается лучшая позиция по pay_for_cart."""
    mock_ch = AsyncMock()
    ts = datetime.now()
    mock_ch.get_conv_cart_to_views = AsyncMock(
        return_value={
            "kw1": [
                ConvCartToViewsOnPosition(keyword="kw1", position=1, conv_cart_to_views=0.06),
                ConvCartToViewsOnPosition(keyword="kw1", position=2, conv_cart_to_views=0.02),
                ConvCartToViewsOnPosition(keyword="kw1", position=3, conv_cart_to_views=0.02),
                ConvCartToViewsOnPosition(keyword="kw1", position=4, conv_cart_to_views=0.05),
                ConvCartToViewsOnPosition(keyword="kw1", position=5, conv_cart_to_views=0.0091),
                ConvCartToViewsOnPosition(keyword="kw1", position=6, conv_cart_to_views=0.0011),
                ConvCartToViewsOnPosition(keyword="kw1", position=7, conv_cart_to_views=0.0001),
                ConvCartToViewsOnPosition(keyword="kw1", position=7, conv_cart_to_views=0.0001),
                ConvCartToViewsOnPosition(keyword="kw1", position=7, conv_cart_to_views=0.0001),
                ConvCartToViewsOnPosition(keyword="kw1", position=7, conv_cart_to_views=0.0001),
            ]
        }
    )
    mock_ch.get_bids_for_positions = AsyncMock(
        return_value={
            "kw1": [
                BidPosition(keyword="kw1", position=1, bid=60, timestamp=datetime.now()),
                BidPosition(keyword="kw1", position=2, bid=80, timestamp=datetime.now() - timedelta(minutes=1)),
                BidPosition(keyword="kw1", position=5, bid=90, timestamp=datetime.now() - timedelta(seconds=30)),
                BidPosition(keyword="kw1", position=300, bid=60, timestamp=datetime.now() - timedelta(seconds=30)),
                BidPosition(keyword="kw1", position=300, bid=60, timestamp=datetime.now() - timedelta(seconds=30)),
            ] * 2
        }
    )

    predictor = PredictKeywordsTargetPlace(mock_ch)
    result = await predictor.get_keywords_target_position(
        nmid=12345, min_bid=50, positions_size=10
    )

    assert result == {"kw1": 1}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_target_position_never_returns_zero():
    """When best_position.position is 0 or negative, result must be >= 1 (never 0)."""
    mock_ch = AsyncMock()
    ts = datetime.now()
    mock_ch.get_conv_cart_to_views = AsyncMock(
        return_value={
            "kw1": [
                ConvCartToViewsOnPosition(keyword="kw1", position=0, conv_cart_to_views=0.1),
                ConvCartToViewsOnPosition(keyword="kw1", position=1, conv_cart_to_views=0.05),
            ]
        }
    )
    mock_ch.get_bids_for_positions = AsyncMock(
        return_value={
            "kw1": [
                BidPosition(keyword="kw1", position=0, bid=60, timestamp=ts),
                BidPosition(keyword="kw1", position=1, bid=80, timestamp=ts),
            ]
        }
    )

    predictor = PredictKeywordsTargetPlace(mock_ch)
    result = await predictor.get_keywords_target_position(
        nmid=12345, min_bid=50, positions_size=10
    )

    assert 0 not in result.values()
    assert result["kw1"] >= 1


@pytest.mark.unit
def test_sort_bids_for_positions():
    """Сортировка ставок по position."""
    predictor = PredictKeywordsTargetPlace(None)
    ts = datetime.now()
    bids = {
        "kw1": [
            BidPosition("kw1", 3, 100, ts),
            BidPosition("kw1", 1, 80, ts),
            BidPosition("kw1", 2, 90, ts),
        ],
    }
    result = PredictKeywordsTargetPlace._sort_bids_for_positions(bids)

    assert [p.position for p in result["kw1"]] == [1, 2, 3]


@pytest.mark.unit
def test_delete_bad_bids_keeps_single_item():
    """Одна ставка должна оставаться без изменений."""
    predictor = PredictKeywordsTargetPlace(None)
    ts = datetime.now()
    items = [BidPosition("kw1", 1, 100, ts)]
    result = PredictKeywordsTargetPlace._delete_bad_bids(items)

    assert len(result) == 1
    assert result[0].position == 1


@pytest.mark.unit
def test_fill_positions_dobivaet_otsutstvuyushchie():
    """Добивка отсутствующих позиций до positions_size."""
    predictor = PredictKeywordsTargetPlace(None)
    ts = datetime.now()
    items = [
        BidPosition("kw1", 1, 100, ts),
        BidPosition("kw1", 3, 120, ts),
    ]
    result = PredictKeywordsTargetPlace._fill_positions(items, min_bid=50, size=5)

    positions = [p.position for p in result]
    assert positions == [1, 2, 3, 4, 5]


@pytest.mark.unit
def test_fill_positions_odnorodnyj_keyword():
    """Все позиции от одного keyword (assert не срабатывает)."""
    predictor = PredictKeywordsTargetPlace(None)
    ts = datetime.now()
    items = [
        BidPosition("kw1", 1, 100, ts),
        BidPosition("kw1", 2, 110, ts),
    ]
    result = PredictKeywordsTargetPlace._fill_positions(items, min_bid=50, size=4)

    assert all(p.keyword == "kw1" for p in result)
    assert len(result) == 4


@pytest.mark.unit
def test_fill_positions_raises_raznye_kluchi():
    """Assert при смешении keyword."""
    predictor = PredictKeywordsTargetPlace(None)
    ts = datetime.now()
    items = [
        BidPosition("kw1", 1, 100, ts),
        BidPosition("kw2", 2, 110, ts),
    ]
    with pytest.raises(AssertionError, match="разных ключей"):
        PredictKeywordsTargetPlace._fill_positions(items, min_bid=50, size=5)


@pytest.mark.unit
def test_fill_positions_convs_prostavlyaet_conv_carts_to_views():
    """Проставление conv_carts_to_views только для совпадающих position."""
    ts = datetime.now()
    positions = [
        BidPosition("kw1", 1, 100, ts),
        BidPosition("kw1", 2, 110, ts),
        BidPosition("kw1", 3, 120, ts),
    ]
    convs = [
        ConvCartToViewsOnPosition("kw1", 1, 0.1),
        ConvCartToViewsOnPosition("kw1", 3, 0.2),
    ]
    result = PredictKeywordsTargetPlace._fill_positions_convs(positions, convs)

    assert result[0].conv_carts_to_views == 0.1
    assert 1 not in result
    assert result[1].conv_carts_to_views == 0.2


@pytest.mark.unit
def test_fill_positions_convs_raises_raznye_kluchi():
    """Assert при несовпадении keyword в positions и convs."""
    predictor = PredictKeywordsTargetPlace(None)
    ts = datetime.now()
    positions = [BidPosition("kw1", 1, 100, ts)]
    convs = [ConvCartToViewsOnPosition("kw2", 1, 0.1)]
    with pytest.raises(AssertionError):
        PredictKeywordsTargetPlace._fill_positions_convs(positions, convs)


@pytest.mark.unit
def test_normalize_bids_for_positions_zapolnyaet_convs():
    """_normalize_bids_for_positions должен использовать convs.get(key) и заполнять conv_carts_to_views."""
    predictor = PredictKeywordsTargetPlace(None)
    ts = datetime.now()
    bids = {
        "kw1": [
            BidPosition("kw1", 1, 100, ts),
            BidPosition("kw1", 2, 110, ts),
            BidPosition("kw1", 3, 120, ts),
        ],
    }
    convs = {
        "kw1": [
            ConvCartToViewsOnPosition("kw1", 1, 0.1),
            ConvCartToViewsOnPosition("kw1", 2, 0.2),
            ConvCartToViewsOnPosition("kw1", 3, 0.15),
        ],
    }
    result = predictor._normalize_bids_for_positions(
        bids, convs, min_bid=50, positions_size=5
    )

    assert "kw1" in result
    for pos in result["kw1"]:
        assert pos.conv_carts_to_views is not None
