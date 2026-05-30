"""Unit: effective STEP_UP / STEP_DOWN по совпадению target_place."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
    target_place_for_v3_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    candidate_for_strategy_mode,
    count_effective_released_aggression_steps,
    iter_effective_upper_modes,
    mode_candidates_same_effective_target,
    resolve_next_effective_step_down,
    resolve_next_effective_step_up,
    target_place_from_mode_candidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    step_up,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)

from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST

RK = RK_ORDERS_PER_CART_TEST
TS = datetime(2024, 1, 1, tzinfo=UTC)


def _fake_catalog_places(
    *,
    min_place: int,
    opt_place: int,
    max_place: int,
    min_bid: float = 500.0,
    opt_bid: float = 500.0,
    max_bid: float = 10_000.0,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """Каталог с заданными target_place; bid может отличаться при том же place."""

    def _mc(mode: AggressionTargetMode, place: int, bid: float) -> ModeCandidate:
        return ModeCandidate(
            mode=mode,
            position=place,
            bid=bid,
            predicted_cpa=100.0,
            is_valid=True,
        )

    return {
        AggressionTargetMode.MIN_CPA: _mc(AggressionTargetMode.MIN_CPA, min_place, min_bid),
        AggressionTargetMode.OPTIMUM: _mc(AggressionTargetMode.OPTIMUM, opt_place, opt_bid),
        AggressionTargetMode.MAX_CONVERSION: _mc(
            AggressionTargetMode.MAX_CONVERSION, max_place, max_bid
        ),
    }


def _places(cat: dict[AggressionTargetMode, ModeCandidate]) -> dict[str, int | None]:
    return {
        "MIN": target_place_from_mode_candidate(
            cat[AggressionTargetMode.MIN_CPA]
        ),
        "OPT": target_place_from_mode_candidate(cat[AggressionTargetMode.OPTIMUM]),
        "MAX": target_place_from_mode_candidate(
            cat[AggressionTargetMode.MAX_CONVERSION]
        ),
    }


@pytest.mark.unit
def test_same_target_place_only_position_not_bid() -> None:
    """Разный bid при одном place — всё равно alias."""
    cat = _fake_catalog_places(
        min_place=40, opt_place=40, max_place=1, min_bid=500.0, opt_bid=999.0
    )
    m = cat[AggressionTargetMode.MIN_CPA]
    o = cat[AggressionTargetMode.OPTIMUM]
    assert mode_candidates_same_effective_target(m, o)
    assert resolve_next_effective_step_up(
        KeywordStrategyMode.MIN_CPA, cat
    ).next_mode == KeywordStrategyMode.MAX_CONVERSION


@pytest.mark.unit
def test_example_1_min_opt_same_place_step_up_to_max() -> None:
    """MIN=40, OPT=40, MAX=1 → UP из MIN сразу в MAX."""
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=1)
    assert _places(cat) == {"MIN": 40, "OPT": 40, "MAX": 1}
    up = resolve_next_effective_step_up(KeywordStrategyMode.MIN_CPA, cat)
    assert up.next_mode == KeywordStrategyMode.MAX_CONVERSION
    assert "OPTIMUM" in up.skipped_aliases[0]
    assert "target_place" in up.skipped_aliases[0]


@pytest.mark.unit
def test_example_2_opt_max_same_place_up_min_to_max() -> None:
    """MIN=40, OPT=1, MAX=1 → UP MIN→MAX (alias OPT); из OPT effective UP нет."""
    cat = _fake_catalog_places(min_place=40, opt_place=1, max_place=1)
    up_min = resolve_next_effective_step_up(KeywordStrategyMode.MIN_CPA, cat)
    assert up_min.next_mode == KeywordStrategyMode.MAX_CONVERSION
    assert any("OPTIMUM" in msg for msg in up_min.skipped_aliases)
    assert resolve_next_effective_step_up(
        KeywordStrategyMode.OPTIMUM, cat
    ).next_mode is None
    assert iter_effective_upper_modes(KeywordStrategyMode.MIN_CPA, cat) == [
        KeywordStrategyMode.MAX_CONVERSION
    ]


@pytest.mark.unit
def test_example_3_all_same_place_no_steps() -> None:
    """MIN=OPT=MAX=1 → между M/O/C действий нет."""
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    assert resolve_next_effective_step_up(KeywordStrategyMode.MIN_CPA, cat).next_mode is None
    assert resolve_next_effective_step_up(KeywordStrategyMode.OPTIMUM, cat).next_mode is None
    assert iter_effective_upper_modes(KeywordStrategyMode.MIN_CPA, cat) == []


@pytest.mark.unit
def test_released_steps_alias_zero_off_or_place_change_one() -> None:
    """released_steps: alias=0, OFF или смена place=1."""
    cat_o_c = _fake_catalog_places(min_place=40, opt_place=1, max_place=1)
    assert (
        count_effective_released_aggression_steps(
            KeywordStrategyMode.MAX_CONVERSION,
            KeywordStrategyMode.OPTIMUM,
            cat_o_c,
        )
        == 0
    )
    assert (
        count_effective_released_aggression_steps(
            KeywordStrategyMode.MAX_CONVERSION,
            KeywordStrategyMode.MIN_CPA,
            cat_o_c,
        )
        == 1
    )
    cat_all = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    assert (
        count_effective_released_aggression_steps(
            KeywordStrategyMode.MAX_CONVERSION,
            KeywordStrategyMode.OPTIMUM,
            cat_all,
        )
        == 0
    )
    assert (
        count_effective_released_aggression_steps(
            KeywordStrategyMode.MAX_CONVERSION,
            KeywordStrategyMode.OFF,
            cat_all,
        )
        == 1
    )


@pytest.mark.unit
def test_step_down_max_to_min_skips_opt_same_place_as_max() -> None:
    """MAX=1, OPT=1, MIN=40 → DOWN из MAX сразу в MIN."""
    cat = _fake_catalog_places(min_place=40, opt_place=1, max_place=1)
    down = resolve_next_effective_step_down(KeywordStrategyMode.MAX_CONVERSION, cat)
    assert down.next_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_full_ladder_three_distinct_places() -> None:
    cat = _fake_catalog_places(min_place=22, opt_place=10, max_place=1)
    assert iter_effective_upper_modes(KeywordStrategyMode.MIN_CPA, cat) == [
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    ]


@pytest.mark.unit
def test_target_place_matches_candidates_helper() -> None:
    """``target_place_from_mode_candidate`` == ``target_place_for_v3_strategy_mode``."""
    prof = [
        PositionProfilePoint(
            position=1, bid=10_000.0, predicted_conversion=0.13, pay_for_cart=1.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=40, bid=500.0, predicted_conversion=0.015, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    cat = build_mode_candidates(
        profile=prof, keyword_text="kw", rk_orders_per_cart=RK
    )
    for mode in (
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    ):
        mc = candidate_for_strategy_mode(mode, cat)
        assert target_place_from_mode_candidate(mc) == target_place_for_v3_strategy_mode(
            mode, cat
        )


@pytest.mark.unit
def test_build_profile_o_eq_m_by_place() -> None:
    """CH-профиль: если MIN и OPT на одном place — effective UP в MAX."""
    prof = [
        PositionProfilePoint(
            position=1, bid=10_000.0, predicted_conversion=0.13, pay_for_cart=1.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=40, bid=500.0, predicted_conversion=0.015, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    cat = build_mode_candidates(
        profile=prof, keyword_text="kw", rk_orders_per_cart=RK
    )
    m = candidate_for_strategy_mode(KeywordStrategyMode.MIN_CPA, cat)
    o = candidate_for_strategy_mode(KeywordStrategyMode.OPTIMUM, cat)
    assert m is not None and o is not None
    if target_place_from_mode_candidate(m) == target_place_from_mode_candidate(o):
        assert (
            resolve_next_effective_step_up(KeywordStrategyMode.MIN_CPA, cat).next_mode
            == KeywordStrategyMode.MAX_CONVERSION
        )


@pytest.mark.unit
def test_logical_step_up_differs_when_place_alias() -> None:
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=1)
    assert step_up(KeywordStrategyMode.MIN_CPA) == KeywordStrategyMode.OPTIMUM
    assert (
        resolve_next_effective_step_up(KeywordStrategyMode.MIN_CPA, cat).next_mode
        == KeywordStrategyMode.MAX_CONVERSION
    )


# --- Edge cases (acceptance) ---


@pytest.mark.unit
def test_edge_off_to_min_ignores_target_place_alias() -> None:
    """OFF → MIN: не сравниваем place; MIN даже при MIN=OPT=MAX на одном place."""
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    assert resolve_next_effective_step_up(KeywordStrategyMode.OFF, cat).next_mode == (
        KeywordStrategyMode.MIN_CPA
    )
    assert iter_effective_upper_modes(KeywordStrategyMode.OFF, cat) == [
        KeywordStrategyMode.MIN_CPA
    ]


@pytest.mark.unit
def test_edge_no_ch_invalid_catalog_min_only_upper_modes() -> None:
    """NO_CH: нет CH-профиля — iter не предлагает OPT/MAX (invalid candidates)."""
    cat = build_mode_candidates(
        profile=None,
        keyword_text="no_ch",
        conv_views_to_orders=0.05,
    )
    assert not cat[AggressionTargetMode.OPTIMUM].is_valid
    assert not cat[AggressionTargetMode.MAX_CONVERSION].is_valid
    assert iter_effective_upper_modes(KeywordStrategyMode.OFF, cat) == [
        KeywordStrategyMode.MIN_CPA
    ]
    assert iter_effective_upper_modes(KeywordStrategyMode.MIN_CPA, cat) == []
    upper_from_off = iter_effective_upper_modes(KeywordStrategyMode.OFF, cat)
    assert KeywordStrategyMode.OPTIMUM not in upper_from_off
    assert KeywordStrategyMode.MAX_CONVERSION not in upper_from_off


@pytest.mark.unit
def test_edge_o_eq_c_single_step_up_chain() -> None:
    """O=C: MIN→MAX один шаг; OPT alias; OPT→MAX нет."""
    cat = _fake_catalog_places(min_place=40, opt_place=1, max_place=1)
    chain = iter_effective_upper_modes(KeywordStrategyMode.MIN_CPA, cat)
    assert chain == [KeywordStrategyMode.MAX_CONVERSION]
    assert resolve_next_effective_step_up(
        KeywordStrategyMode.OPTIMUM, cat
    ).next_mode is None


@pytest.mark.unit
def test_edge_o_eq_m_skip_opt_step_up_to_max() -> None:
    """O=M: MIN→MAX, MIN→OPT не в effective chain."""
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=1)
    assert iter_effective_upper_modes(KeywordStrategyMode.MIN_CPA, cat) == [
        KeywordStrategyMode.MAX_CONVERSION
    ]
    assert resolve_next_effective_step_up(
        KeywordStrategyMode.MIN_CPA, cat
    ).next_mode == KeywordStrategyMode.MAX_CONVERSION
