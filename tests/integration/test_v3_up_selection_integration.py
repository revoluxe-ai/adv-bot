"""Интеграция V3: cost-first UP через ``plan_one_up_by_policy`` (pooled planner)."""

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
    plan_one_up_by_policy,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.auto_updater_v3.conftest import ctx

pytestmark = pytest.mark.integration


def _ladder_profile() -> list[PositionProfilePoint]:
    ts = datetime(2024, 6, 1, tzinfo=UTC)
    return [
        PositionProfilePoint(
            position=1,
            bid=120,
            predicted_conversion=0.05,
            pay_for_cart=80.0,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=2,
            bid=90,
            predicted_conversion=0.04,
            pay_for_cart=25.0,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=3,
            bid=70,
            predicted_conversion=0.03,
            pay_for_cart=12.0,
            timestamp=ts,
        ),
    ]


@pytest.mark.integration
def test_v3_underperform_cost_first_jump_via_pooled_planner() -> None:
    """E2E pooled UP: один UP, target — режим с минимальным state_cost."""
    prof = _ladder_profile()
    contexts = [ctx(ks_id=42, mode=KeywordStrategyMode.OFF, profile=prof)]
    prepared = build_prepared_from_contexts(contexts)
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    actions = plan_one_up_by_policy(prepared, policy=policy)
    assert len(actions) == 1
    act = actions[0]
    assert act.action == V3ActionType.UP
    assert act.keyword_setting_id == 42
    assert act.target_strategy_mode is not None
    assert act.selection_log is not None
    assert act.selection_log.state_cost is not None
