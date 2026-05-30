"""Unit: M3 ``plan_headroom_plus_one`` с effective transitions (O=M alias)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_headroom_plus_one,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
    collect_transition_candidates,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.auto_updater_v3.conftest import ctx
from tests.unit.auto_updater_v3.test_effective_ladder_steps import _fake_catalog_places

TS = datetime(2024, 1, 1, tzinfo=UTC)


def _o_eq_m_profile() -> list[PositionProfilePoint]:
    return [
        PositionProfilePoint(
            position=1, bid=10_000, predicted_conversion=0.13, pay_for_cart=50.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=40, bid=500, predicted_conversion=0.015, pay_for_cart=10.0, timestamp=TS
        ),
    ]


@pytest.mark.unit
def test_collect_transition_min_to_max_when_o_eq_m(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O=M: effective UP из MIN — только MAX (логический jump +2)."""
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=1)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking._catalog_for_ctx",
        lambda _ctx, _prepared=None, **_kwargs: cat,
    )
    prepared = build_prepared_from_contexts(
        [ctx(ks_id=7, mode=KeywordStrategyMode.MIN_CPA, profile=_o_eq_m_profile())]
    )
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    candidates = collect_transition_candidates(prepared, policy=policy)
    min_up = [c for c in candidates if c.from_mode == KeywordStrategyMode.MIN_CPA]
    assert len(min_up) == 1
    assert min_up[0].to_mode == KeywordStrategyMode.MAX_CONVERSION
    assert mode_level(min_up[0].to_mode) == mode_level(min_up[0].from_mode) + 2
    assert KeywordStrategyMode.OPTIMUM not in {c.to_mode for c in candidates}


@pytest.mark.unit
def test_plan_headroom_plus_one_up_to_max_when_o_eq_m(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M3 headroom: MIN→MAX effective UP, не пустой список из-за +1 filter."""
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=1)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking._catalog_for_ctx",
        lambda _ctx, _prepared=None, **_kwargs: cat,
    )
    prepared = build_prepared_from_contexts(
        [ctx(ks_id=8, mode=KeywordStrategyMode.MIN_CPA, profile=_o_eq_m_profile())]
    )
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    actions = plan_headroom_plus_one(
        prepared,
        resolve=100.0,
        fact_pay_for_order=50.0,
        policy=policy,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].keyword_setting_id == 8
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MAX_CONVERSION
    assert actions[0].reason == "m3_headroom_plus_one"


@pytest.mark.unit
def test_plan_headroom_plus_one_empty_without_headroom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Без headroom (fact >= 0.9 * resolve) — []."""
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=1)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking._catalog_for_ctx",
        lambda _ctx, _prepared=None, **_kwargs: cat,
    )
    prepared = build_prepared_from_contexts(
        [ctx(ks_id=9, mode=KeywordStrategyMode.MIN_CPA, profile=_o_eq_m_profile())]
    )
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    assert (
        plan_headroom_plus_one(
            prepared,
            resolve=100.0,
            fact_pay_for_order=95.0,
            policy=policy,
        )
        == []
    )
