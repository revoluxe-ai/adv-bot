"""Тесты ``new_bid_calculate``: snap и согласование min/max.

Политика (как в докстринге ``new_bids_calculator``): при ``snap_to_min_bid_no_keyword_target``
ставка принудительно к минимуму WB; ``max_bid`` не ограничивает эту ветку. В обычном
режиме после клампа по ``max_bid`` ставка не остаётся ниже ``min_bid`` (подъём до min
со статусом BAD).
"""

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


@pytest.mark.unit
def test_snap_to_min_uses_platform_min_when_min_exceeds_user_max() -> None:
    """Same as snap semantics: WB minimum wins over user max_cpm."""
    inp = CalculationInput(
        adv_id=1,
        nmid=99,
        cluster="kw",
        current_bid=200,
        current_position=10.0,
        target_position=5,
        step=10,
        max_bid=100,
        min_bid=150,
        predict_target_bids=None,
        snap_to_min_bid_no_keyword_target=True,
    )
    out = new_bid_calculate(inp)
    assert out is not None
    assert out.new_bid == 150
    assert out.bidder_keyword_status == BidderKeywordStatus.GOOD


@pytest.mark.unit
def test_snap_to_min_result_independent_of_target_position() -> None:
    """В snap-ветке итог не зависит от target_position (None vs экстремум)."""
    common = dict(
        adv_id=1,
        nmid=99,
        cluster="kw",
        current_bid=200,
        current_position=10.0,
        step=10,
        max_bid=500,
        min_bid=50,
        predict_target_bids=None,
        snap_to_min_bid_no_keyword_target=True,
    )
    out_none = new_bid_calculate(CalculationInput(**common, target_position=None))
    out_big = new_bid_calculate(CalculationInput(**common, target_position=9999))
    assert out_none is not None and out_big is not None
    assert out_none.new_bid == out_big.new_bid == 50
    assert out_none.direct == out_big.direct


@pytest.mark.unit
def test_normal_mode_returns_none_when_target_position_missing() -> None:
    """Обычный режим без target_position: не считаем ставку (как при отсутствии min_bid)."""
    inp = CalculationInput(
        adv_id=42,
        nmid=7,
        cluster="cluster_x",
        current_bid=100,
        current_position=5.0,
        target_position=None,
        step=10,
        max_bid=500,
        min_bid=50,
        predict_target_bids=None,
        snap_to_min_bid_no_keyword_target=False,
    )
    assert new_bid_calculate(inp) is None


@pytest.mark.unit
def test_normal_path_after_max_clamp_snaps_up_to_min_when_min_above_max() -> None:
    """If max clamp would sit below platform min, raise to min (align with snap branch)."""
    inp = CalculationInput(
        adv_id=1,
        nmid=99,
        cluster="kw",
        current_bid=280,
        current_position=10.0,
        target_position=5,
        step=50,
        max_bid=300,
        min_bid=400,
        predict_target_bids=None,
        snap_to_min_bid_no_keyword_target=False,
    )
    out = new_bid_calculate(inp)
    assert out is not None
    assert out.new_bid == 400
    assert out.bidder_keyword_status == BidderKeywordStatus.BAD
