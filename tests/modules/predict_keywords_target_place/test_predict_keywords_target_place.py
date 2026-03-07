"""Unit tests for PredictKeywordsTargetPlace."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.bids_for_positions_manager.dto import BidPositionRow
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import (
    BidPosition,
    ConvCartToViewsOnPosition,
)
from app.modules.predict_keywords_target_place.predict_keywords_target_place import (
    PredictKeywordsTargetPlace,
)


def _make_adv(
    main_nmid: int = 12345,
    min_bid: int = 50,
    strategy: Strategy = Strategy.MIN_CPO,
) -> MagicMock:
    adv = MagicMock()
    adv.main_nmid = main_nmid
    adv.search_adv_min_bids = {main_nmid: min_bid}
    adv.strategy = strategy
    return adv


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_target_position_calls_ch_and_bids_manager():
    """Проверяем, что get_conv_cart_to_views и get_bid_positions_normalized вызываются."""
    mock_ch = AsyncMock()
    mock_ch.get_conv_cart_to_views = AsyncMock(return_value={})
    mock_bids_manager = AsyncMock()
    mock_bids_manager.get_bid_positions_normalized = AsyncMock(return_value={})

    predictor = PredictKeywordsTargetPlace(mock_ch, mock_bids_manager)
    adv = _make_adv(main_nmid=12345, min_bid=50)
    result = await predictor.get_keywords_target_position(adv=adv, positions_size=10)

    mock_ch.get_conv_cart_to_views.assert_called_once_with(nmid=12345, positions_size=10)
    mock_bids_manager.get_bid_positions_normalized.assert_called_once_with(
        nmid=12345, min_bid=50, positions_size=10
    )
    assert result == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_target_position_returns_empty_when_empty_data():
    """При пустых convs и rows возвращается пустой словарь."""
    mock_ch = AsyncMock()
    mock_ch.get_conv_cart_to_views = AsyncMock(return_value={})
    mock_bids_manager = AsyncMock()
    mock_bids_manager.get_bid_positions_normalized = AsyncMock(return_value={})

    predictor = PredictKeywordsTargetPlace(mock_ch, mock_bids_manager)
    adv = _make_adv(main_nmid=12345, min_bid=50)
    result = await predictor.get_keywords_target_position(adv=adv, positions_size=10)

    assert result == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_target_position_returns_best_position_when_valid_data():
    """При валидных convs и rows возвращается лучшая позиция по pay_for_cart."""
    mock_ch = AsyncMock()
    mock_ch.get_conv_cart_to_views = AsyncMock(
        return_value={
            "kw1": [
                ConvCartToViewsOnPosition("kw1", 1, 0.06),
                ConvCartToViewsOnPosition("kw1", 2, 0.02),
                ConvCartToViewsOnPosition("kw1", 3, 0.02),
                ConvCartToViewsOnPosition("kw1", 4, 0.05),
                ConvCartToViewsOnPosition("kw1", 5, 0.0091),
                ConvCartToViewsOnPosition("kw1", 6, 0.0011),
                ConvCartToViewsOnPosition("kw1", 7, 0.0001),
            ]
            + [ConvCartToViewsOnPosition("kw1", 7, 0.0001)] * 3,
        }
    )
    ts = datetime.now()
    mock_bids_manager = AsyncMock()
    mock_bids_manager.get_bid_positions_normalized = AsyncMock(
        return_value={
            "kw1": [
                BidPositionRow("kw1", 1, 60, ts),
                BidPositionRow("kw1", 2, 80, ts - timedelta(minutes=1)),
                BidPositionRow("kw1", 5, 90, ts - timedelta(seconds=30)),
                BidPositionRow("kw1", 300, 60, ts - timedelta(seconds=30)),
            ]
            * 2,
        }
    )

    predictor = PredictKeywordsTargetPlace(mock_ch, mock_bids_manager)
    adv = _make_adv(main_nmid=12345, min_bid=50, strategy=Strategy.MIN_CPO)
    result = await predictor.get_keywords_target_position(adv=adv, positions_size=10)

    assert result == {"kw1": 1}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_target_position_returns_best_conv_when_strategy_max_conv():
    """При MAX_CONV выбор идет только по conv_carts_to_views, без учета ставки."""
    mock_ch = AsyncMock()
    ts = datetime.now()
    mock_ch.get_conv_cart_to_views = AsyncMock(
        return_value={
            "kw1": [
                ConvCartToViewsOnPosition(keyword="kw1", position=1, conv_cart_to_views=0.1),
                ConvCartToViewsOnPosition(keyword="kw1", position=2, conv_cart_to_views=0.2),
            ]
        }
    )
    mock_bids_manager = AsyncMock()
    mock_bids_manager.get_bid_positions_normalized = AsyncMock(
        return_value={
            "kw1": [
                BidPositionRow("kw1", 1, 60, ts),
                BidPositionRow("kw1", 2, 300, ts),
            ]
        }
    )

    predictor = PredictKeywordsTargetPlace(mock_ch, mock_bids_manager)
    adv = _make_adv(main_nmid=12345, min_bid=50, strategy=Strategy.MAX_CONV)
    result = await predictor.get_keywords_target_position(adv=adv, positions_size=10)

    assert result == {"kw1": 2}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_target_position_never_returns_zero():
    """When best_position.position is 0 or negative, result must be >= 1 (never 0)."""
    mock_ch = AsyncMock()
    mock_ch.get_conv_cart_to_views = AsyncMock(
        return_value={
            "kw1": [
                ConvCartToViewsOnPosition("kw1", 0, 0.1),
                ConvCartToViewsOnPosition("kw1", 1, 0.05),
            ]
        }
    )
    ts = datetime.now()
    mock_bids_manager = AsyncMock()
    mock_bids_manager.get_bid_positions_normalized = AsyncMock(
        return_value={
            "kw1": [
                BidPositionRow("kw1", 0, 60, ts),
                BidPositionRow("kw1", 1, 80, ts),
            ]
        }
    )

    predictor = PredictKeywordsTargetPlace(mock_ch, mock_bids_manager)
    adv = _make_adv(main_nmid=12345, min_bid=50)
    result = await predictor.get_keywords_target_position(adv=adv, positions_size=10)

    assert 0 not in result.values()
    assert result["kw1"] >= 1


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

    assert len(result) == 2
    assert result[0].conv_carts_to_views == 0.1
    assert result[1].conv_carts_to_views == 0.2


@pytest.mark.unit
def test_fill_positions_convs_raises_raznye_kluchi():
    """Assert при несовпадении keyword в positions и convs."""
    ts = datetime.now()
    positions = [BidPosition("kw1", 1, 100, ts)]
    convs = [ConvCartToViewsOnPosition("kw2", 1, 0.1)]
    with pytest.raises(AssertionError):
        PredictKeywordsTargetPlace._fill_positions_convs(positions, convs)


@pytest.mark.unit
def test_map_rows_to_bid_positions_fills_convs():
    """_map_rows_to_bid_positions использует convs и заполняет conv_carts_to_views."""
    mock_ch = AsyncMock()
    mock_bids = AsyncMock()
    predictor = PredictKeywordsTargetPlace(mock_ch, mock_bids)
    ts = datetime.now()
    rows = {
        "kw1": [
            BidPositionRow("kw1", 1, 100, ts),
            BidPositionRow("kw1", 2, 110, ts),
            BidPositionRow("kw1", 3, 120, ts),
        ],
    }
    convs = {
        "kw1": [
            ConvCartToViewsOnPosition("kw1", 1, 0.1),
            ConvCartToViewsOnPosition("kw1", 2, 0.2),
            ConvCartToViewsOnPosition("kw1", 3, 0.15),
        ],
    }
    result = predictor._map_rows_to_bid_positions(rows, convs)

    assert "kw1" in result
    for pos in result["kw1"]:
        assert pos.conv_carts_to_views is not None
