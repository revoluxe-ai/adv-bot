"""Unit: нормализованный OPTIMUM и паритет candidates ↔ predict."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place.clickhouse_manager.dto.bid_position import (
    BidPosition,
)
from app.modules.predict_keywords_target_place.predict_keywords_target_place import (
    PredictKeywordsTargetPlace,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
    target_place_for_v3_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)
from app.modules.shop_runner.service_manager.services.v3_optimum_balance import (
    OPTIMUM_MAX_CPO_PENALTY_COMPARE,
    normalized_optimum_score,
    normalized_point_metrics,
    select_optimum_row,
    select_optimum_row_cpo_cap,
    select_optimum_row_production,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    profile_points_from_bid_positions,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from unittest.mock import AsyncMock

from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST

CONV_V2 = 0.01
RK = RK_ORDERS_PER_CART_TEST


def _tradeoff_profile() -> list[PositionProfilePoint]:
    """M на глубокой позиции, C на топе, O — компромисс посередине."""
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        PositionProfilePoint(
            position=1,
            bid=20_000,
            predicted_conversion=0.04,
            pay_for_cart=100.0,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=10,
            bid=800,
            predicted_conversion=0.025,
            pay_for_cart=20.0,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=22,
            bid=500,
            predicted_conversion=0.015,
            pay_for_cart=15.0,
            timestamp=ts,
        ),
    ]


def _tradeoff_bid_positions(keyword: str = "kw") -> list[BidPosition]:
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    out: list[BidPosition] = []
    for pos, bid, conv in ((1, 20_000, 0.04), (10, 800, 0.025), (22, 500, 0.015)):
        bp = BidPosition(keyword, pos, bid, ts)
        bp.conv_carts_to_views = conv
        out.append(bp)
    return out


@pytest.mark.unit
def test_optimum_picks_intermediate_not_min_or_max_conv() -> None:
    """С RK ratio: MIN/O на лучшем CPO (поз.10), C на топе conv (поз.1)."""
    cand = build_mode_candidates(
        profile=_tradeoff_profile(),
        keyword_text="kw",
        rk_orders_per_cart=RK,
    )
    assert cand[AggressionTargetMode.MIN_CPA].position == 10
    assert cand[AggressionTargetMode.MAX_CONVERSION].position == 1
    opt = cand[AggressionTargetMode.OPTIMUM]
    assert opt.is_valid
    assert opt.position == 10
    assert opt.position != cand[AggressionTargetMode.MAX_CONVERSION].position


@pytest.mark.unit
def test_optimum_not_equal_max_on_tradeoff_profile() -> None:
    cand = build_mode_candidates(
        profile=_tradeoff_profile(),
        keyword_text="kw",
        rk_orders_per_cart=RK,
    )
    opt = cand[AggressionTargetMode.OPTIMUM]
    max_c = cand[AggressionTargetMode.MAX_CONVERSION]
    assert opt.is_valid and max_c.is_valid
    assert opt.position != max_c.position


@pytest.mark.unit
def test_optimum_conv_flat_picks_min_cpo() -> None:
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    prof = [
        PositionProfilePoint(
            position=1, bid=1000, predicted_conversion=0.02, pay_for_cart=10.0, timestamp=ts
        ),
        PositionProfilePoint(
            position=2, bid=500, predicted_conversion=0.02, pay_for_cart=5.0, timestamp=ts
        ),
    ]
    cand = build_mode_candidates(
        profile=prof, keyword_text="kw", rk_orders_per_cart=RK
    )
    assert cand[AggressionTargetMode.OPTIMUM].position == 2


@pytest.mark.unit
def test_optimum_cpo_flat_picks_max_conv() -> None:
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    prof = [
        PositionProfilePoint(
            position=1, bid=100, predicted_conversion=0.03, pay_for_cart=1.0, timestamp=ts
        ),
        PositionProfilePoint(
            position=2, bid=100, predicted_conversion=0.01, pay_for_cart=1.0, timestamp=ts
        ),
    ]
    cand = build_mode_candidates(
        profile=prof, keyword_text="kw", rk_orders_per_cart=RK
    )
    assert cand[AggressionTargetMode.OPTIMUM].position == 1


@pytest.mark.unit
def test_candidates_and_predict_same_optimum_target() -> None:
    """Паритет OPTIMUM target_place при одном профиле и conv V2."""
    predictor = PredictKeywordsTargetPlace(AsyncMock(), AsyncMock())
    bids = _tradeoff_bid_positions()
    points = profile_points_from_bid_positions(bids)
    cand = build_mode_candidates(
        profile=points,
        keyword_text="kw",
        rk_orders_per_cart=RK,
    )
    from_candidates = target_place_for_v3_strategy_mode(
        KeywordStrategyMode.OPTIMUM, cand
    )
    from_predict = predictor.get_target_position_for_strategy_mode(
        bids,
        KeywordStrategyMode.OPTIMUM,
        rk_orders_per_cart=RK,
    )
    assert from_candidates == from_predict == 10


@pytest.mark.unit
def test_min_cpa_predict_uses_order_cpo_when_conv_provided() -> None:
    """MIN: CPO заказа (V3), не min pay_for_cart по корзине."""
    predictor = PredictKeywordsTargetPlace(AsyncMock(), AsyncMock())
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    positions = [
        BidPosition("kw", 1, 400, ts),
        BidPosition("kw", 2, 100, ts),
    ]
    positions[0].conv_carts_to_views = 0.5
    positions[1].conv_carts_to_views = 0.01

    legacy_min = predictor.get_target_position_for_strategy_mode(
        positions, KeywordStrategyMode.MIN_CPA
    )
    v3_min = predictor.get_target_position_for_strategy_mode(
        positions,
        KeywordStrategyMode.MIN_CPA,
        rk_orders_per_cart=RK,
    )
    assert legacy_min == 1
    assert v3_min == 1


@pytest.mark.unit
def test_normalized_score_degeneracy() -> None:
    """conv flat → conv_n=1; cpo flat → economy_n=1."""
    assert normalized_optimum_score(
        0.02, 5.0, conv_min=0.02, conv_max=0.02, cpo_min=5.0, cpo_max=20.0
    ) == 1.0
    assert normalized_optimum_score(
        0.03, 10.0, conv_min=0.01, conv_max=0.03, cpo_min=10.0, cpo_max=10.0
    ) == 1.0


@pytest.mark.unit
def test_degenerate_equal_cpo_cpa_n_zero_economy_n_invariant() -> None:
    """Одинаковый CPO: cpa_n=0, economy_n=1 (economy_n = 1 - cpa_n); score → max conv."""
    cpo_flat = 10.0
    conv_lo, conv_hi = 0.01, 0.03
    m_lo = normalized_point_metrics(
        conv_lo,
        cpo_flat,
        conv_min=conv_lo,
        conv_max=conv_hi,
        cpo_min=cpo_flat,
        cpo_max=cpo_flat,
    )
    m_hi = normalized_point_metrics(
        conv_hi,
        cpo_flat,
        conv_min=conv_lo,
        conv_max=conv_hi,
        cpo_min=cpo_flat,
        cpo_max=cpo_flat,
    )
    for m in (m_lo, m_hi):
        assert m.cpa_n == 0.0
        assert m.economy_n == 1.0
        assert m.economy_n == pytest.approx(1.0 - m.cpa_n)

    ts = datetime(2024, 1, 1, tzinfo=UTC)
    prof = [
        PositionProfilePoint(
            position=1, bid=100, predicted_conversion=0.03, pay_for_cart=1.0, timestamp=ts
        ),
        PositionProfilePoint(
            position=2, bid=100, predicted_conversion=0.01, pay_for_cart=1.0, timestamp=ts
        ),
    ]
    cand = build_mode_candidates(
        profile=prof, keyword_text="kw", rk_orders_per_cart=RK
    )
    assert cand[AggressionTargetMode.OPTIMUM].position == 1
    assert cand[AggressionTargetMode.MAX_CONVERSION].position == 1


@pytest.mark.unit
def test_optimum_excludes_max_conv_row() -> None:
    """Верхняя точка (MAX) не должна побеждать в OPTIMUM при наличии trade-off."""
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    prof = [
        PositionProfilePoint(
            position=1,
            bid=6449,
            predicted_conversion=0.1298,
            pay_for_cart=50.0,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=10,
            bid=2000,
            predicted_conversion=0.05,
            pay_for_cart=40.0,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=40,
            bid=510,
            predicted_conversion=0.0153,
            pay_for_cart=33.0,
            timestamp=ts,
        ),
    ]
    cand = build_mode_candidates(
        profile=prof, keyword_text="top_heavy", rk_orders_per_cart=RK
    )
    assert cand[AggressionTargetMode.MAX_CONVERSION].position == 1
    assert cand[AggressionTargetMode.MIN_CPA].position == 40
    opt = cand[AggressionTargetMode.OPTIMUM]
    assert opt.is_valid
    assert opt.position != cand[AggressionTargetMode.MAX_CONVERSION].position


@pytest.mark.unit
def test_select_optimum_tie_break_lower_cpo() -> None:
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    p_high = BidPosition("kw", 1, 100, ts)
    p_low = BidPosition("kw", 2, 100, ts)
    rows = [
        (p_high, 0.02, 20.0),
        (p_low, 0.02, 10.0),
    ]
    pick = select_optimum_row(rows)
    assert pick is not None
    assert pick.cpo == 10.0
    assert pick.row.position == 2


@pytest.mark.unit
def test_compare_cap_constant_is_1_5() -> None:
    assert OPTIMUM_MAX_CPO_PENALTY_COMPARE == 1.5


@pytest.mark.unit
def test_production_optimum_equals_balance_current() -> None:
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    top = PositionProfilePoint(position=1, bid=10_000, predicted_conversion=0.13, timestamp=ts)
    mid = PositionProfilePoint(position=40, bid=500, predicted_conversion=0.015, timestamp=ts)
    rows = [(top, 0.13, 400.0), (mid, 0.015, 100.0)]
    prod = select_optimum_row_production(rows)
    balance = select_optimum_row(rows, mode="current")
    assert prod is not None and balance is not None
    assert (prod.row.position, prod.row.bid) == (
        balance.row.position,
        balance.row.bid,
    )


@pytest.mark.unit
def test_production_may_match_max_when_top_wins_balance() -> None:
    """Честный balance: OPTIMUM может совпасть с MAX (O=C допустимо)."""
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    prof = [
        PositionProfilePoint(
            position=1, bid=500, predicted_conversion=0.13, timestamp=ts
        ),
        PositionProfilePoint(
            position=40, bid=500, predicted_conversion=0.01, timestamp=ts
        ),
    ]
    cand = build_mode_candidates(
        profile=prof, keyword_text="cheap_max", rk_orders_per_cart=RK
    )
    assert cand[AggressionTargetMode.MAX_CONVERSION].position == 1
    opt = cand[AggressionTargetMode.OPTIMUM]
    assert opt.is_valid
    assert opt.position == cand[AggressionTargetMode.MAX_CONVERSION].position


@pytest.mark.unit
def test_select_optimum_cpo_cap_excludes_expensive_top() -> None:
    """CPO-cap 1.3: OPTIMUM не на дорогой top-conv точке."""
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    top = PositionProfilePoint(position=1, bid=10_000, predicted_conversion=0.13, timestamp=ts)
    mid = PositionProfilePoint(position=40, bid=500, predicted_conversion=0.015, timestamp=ts)
    rows = [
        (top, 0.13, 400.0),
        (mid, 0.015, 100.0),
    ]
    pick = select_optimum_row_cpo_cap(rows, max_cpo_penalty=1.3)
    assert pick is not None
    assert pick.row.position == 40
    assert pick.cpo <= 100.0 * 1.3 + 1e-6


@pytest.mark.unit
def test_select_optimum_cpo_cap_allows_cheap_max() -> None:
    """Variant C: если MAX в cap-пуле и выигрывает balance — совпадает с C."""
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    top = PositionProfilePoint(position=1, bid=500, predicted_conversion=0.13, timestamp=ts)
    deep = PositionProfilePoint(position=40, bid=500, predicted_conversion=0.01, timestamp=ts)
    rows = [
        (top, 0.13, 100.0),
        (deep, 0.01, 105.0),
    ]
    pick = select_optimum_row_cpo_cap(rows, max_cpo_penalty=1.3)
    assert pick is not None
    assert pick.row.position == 1
