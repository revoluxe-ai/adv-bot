"""Unit: effective steps в PROFITABLE_EXPANSION / transition_ranking."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    resolve_keyword_v3_eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_profitable_expansion,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
    collect_transition_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST
from tests.unit.test_auto_updater_v3 import _calc_kw, _conv_for_pay_for_order

RK = RK_ORDERS_PER_CART_TEST
TS = datetime(2024, 1, 1, tzinfo=UTC)


def _policy() -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.UNKNOWN,
        aggressiveness=3,
    )


def _ctx_min_alias_o(
    *,
    ks_id: int = 90,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
) -> KeywordV3Context:
    """M=O на pos40, C на pos1 — UP из MIN должен идти в MAX."""
    prof = [
        PositionProfilePoint(
            position=1, bid=10_000.0, predicted_conversion=0.13, pay_for_cart=1.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=40, bid=500.0, predicted_conversion=0.015, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(
        ks_id=ks_id,
        text="alias_o_m",
        mode=mode,
        rating=5.0,
        conv=0.01,
        hard_status=2,
    )
    return KeywordV3Context(keyword=kw, position_profile=prof)


@pytest.mark.unit
def test_profitable_expansion_skips_opt_alias_jumps_to_max() -> None:
    ctx = _ctx_min_alias_o()
    prepared = build_prepared_from_contexts([ctx])
    actions = plan_profitable_expansion(
        prepared,
        resolve=10_000.0,
        policy=_policy(),
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MAX_CONVERSION


@pytest.mark.unit
def test_collect_transition_candidates_skips_opt_alias() -> None:
    ctx = _ctx_min_alias_o()
    prepared = build_prepared_from_contexts([ctx])
    cands = collect_transition_candidates(prepared, policy=_policy())
    to_modes = {c.to_mode for c in cands if c.keyword_setting_id == 90}
    assert KeywordStrategyMode.OPTIMUM not in to_modes
    assert KeywordStrategyMode.MAX_CONVERSION in to_modes


@pytest.mark.unit
def test_edge_off_to_min_expansion_when_m_o_c_same_place() -> None:
    """OFF + degenerate ladder: expansion → MIN_CPA (не MAX)."""
    prof = [
        PositionProfilePoint(
            position=1, bid=510.0, predicted_conversion=0.13, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(
        ks_id=92,
        text="off_deg",
        mode=KeywordStrategyMode.OFF,
        rating=5.0,
        conv=0.01,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    actions = plan_profitable_expansion(
        prepared,
        resolve=10_000.0,
        policy=_policy(),
    )
    assert len(actions) == 1
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_edge_no_ch_off_to_min_only_no_opt_max() -> None:
    """NO_CH MIN-only: OFF→MIN, без OPT/MAX в expansion."""
    no_ch_kw = _calc_kw(
        ks_id=93,
        text="no_ch_edge",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=_conv_for_pay_for_order(49.0),
    )
    ctx = KeywordV3Context(keyword=no_ch_kw, position_profile=None)
    prepared = build_prepared_from_contexts([ctx])
    elig_map = {93: resolve_keyword_v3_eligibility(ctx, [ctx])}
    ladder_inputs = LadderInputs.from_contexts([ctx])
    actions = plan_profitable_expansion(
        prepared,
        resolve=100.0,
        policy=_policy(),
        ladder_inputs=ladder_inputs,
        eligibility_by_ks_id=elig_map,
    )
    assert len(actions) == 1
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    modes = {a.target_strategy_mode for a in actions}
    assert KeywordStrategyMode.OPTIMUM not in modes
    assert KeywordStrategyMode.MAX_CONVERSION not in modes


@pytest.mark.unit
def test_edge_o_eq_c_expansion_single_up_to_max() -> None:
    """O=C: из MIN один UP в MAX (OPT alias), без отдельного OPT→MAX."""
    prof = [
        PositionProfilePoint(
            position=1, bid=10_000.0, predicted_conversion=0.13, pay_for_cart=1.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=40, bid=500.0, predicted_conversion=0.015, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(ks_id=94, text="o_eq_c", mode=KeywordStrategyMode.MIN_CPA, rating=5.0, conv=0.01)
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    actions = plan_profitable_expansion(
        prepared,
        resolve=10_000.0,
        policy=_policy(),
    )
    assert len(actions) == 1
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MAX_CONVERSION
    assert actions[0].target_strategy_mode != KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_degenerate_m_o_c_no_up_from_min() -> None:
    """M=O=C: expansion не создаёт UP."""
    prof = [
        PositionProfilePoint(
            position=1, bid=510.0, predicted_conversion=0.13, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(ks_id=91, text="deg", mode=KeywordStrategyMode.MIN_CPA, rating=1.0, conv=0.01)
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    actions = plan_profitable_expansion(
        prepared,
        resolve=10_000.0,
        policy=_policy(),
    )
    assert actions == []
