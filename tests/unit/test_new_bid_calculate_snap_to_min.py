"""Unit tests for new_bid_calculate snap_to_min_bid_no_keyword_target."""

import pytest

from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.calculation_input import (
    CalculationInput,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.new_bids_calculator import (
    new_bid_calculate,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
    DirectEnum,
)
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import (
    BidderKeywordStatus,
)


@pytest.mark.unit
def test_snap_to_min_returns_min_when_current_above_min() -> None:
    inp = CalculationInput(
        adv_id=1,
        nmid=99,
        cluster="kw",
        current_bid=200,
        current_position=10.0,
        target_position=5,
        step=10,
        max_bid=500,
        min_bid=50,
        predict_target_bids=None,
        snap_to_min_bid_no_keyword_target=True,
    )
    out = new_bid_calculate(inp)
    assert out is not None
    assert out.new_bid == 50
    assert out.direct == DirectEnum.DOWN
    assert out.bidder_keyword_status == BidderKeywordStatus.GOOD


@pytest.mark.unit
def test_snap_to_min_returns_none_when_already_at_min() -> None:
    inp = CalculationInput(
        adv_id=1,
        nmid=99,
        cluster="kw",
        current_bid=50,
        current_position=10.0,
        target_position=5,
        step=10,
        max_bid=500,
        min_bid=50,
        predict_target_bids=None,
        snap_to_min_bid_no_keyword_target=True,
    )
    assert new_bid_calculate(inp) is None


@pytest.mark.unit
def test_snap_to_min_returns_none_when_min_bid_missing() -> None:
    inp = CalculationInput(
        adv_id=1,
        nmid=99,
        cluster="kw",
        current_bid=200,
        current_position=10.0,
        target_position=5,
        step=10,
        max_bid=500,
        min_bid=None,
        predict_target_bids=None,
        snap_to_min_bid_no_keyword_target=True,
    )
    assert new_bid_calculate(inp) is None


@pytest.mark.unit
def test_snap_to_min_raises_to_min_when_current_below_min() -> None:
    inp = CalculationInput(
        adv_id=1,
        nmid=99,
        cluster="kw",
        current_bid=30,
        current_position=10.0,
        target_position=5,
        step=10,
        max_bid=500,
        min_bid=50,
        predict_target_bids=None,
        snap_to_min_bid_no_keyword_target=True,
    )
    out = new_bid_calculate(inp)
    assert out is not None
    assert out.new_bid == 50
    assert out.direct == DirectEnum.UP
