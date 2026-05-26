"""Интеграция V3: cost-first UP с синтетическим профилем (jump OFF→режим с min state_cost)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
    select_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    plan_cost_first_up_one,
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
def test_v3_underperform_cost_first_jump_via_selector() -> None:
    """E2E на уровне selector: один UP, target — режим с минимальным state_cost."""
    prof = _ladder_profile()
    prepared: list[tuple[KeywordV3Context, KeywordStrategyMode, bool]] = [
        (ctx(ks_id=42, mode=KeywordStrategyMode.OFF, profile=prof), KeywordStrategyMode.OFF, False)
    ]
    actions = select_v3_actions(
        state=SalesStates.UNDERPERFORM,
        contexts=[p[0] for p in prepared],
        shelf_promotion_active=False,
        rollout_aggressiveness=3,
    )
    assert len(actions) == 1
    act = actions[0]
    assert act.action == V3ActionType.UP
    assert act.keyword_setting_id == 42
    assert act.target_strategy_mode is not None
    assert act.selection_log is not None
    assert act.selection_log.state_cost is not None


@pytest.mark.integration
def test_v3_plan_cost_first_organic_dominant() -> None:
    prof = _ladder_profile()
    prepared = [
        (ctx(ks_id=7, mode=KeywordStrategyMode.OFF, profile=prof), KeywordStrategyMode.OFF, False)
    ]
    actions = plan_cost_first_up_one(
        prepared,
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        layered=False,
        aggressiveness=V3RolloutAggressiveness.MAX,
        piecewise_shelf=False,
    )
    assert actions[0].action == V3ActionType.UP
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
