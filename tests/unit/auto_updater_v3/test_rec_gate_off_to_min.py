"""Unit: rec gate на полке — OFF→MIN по экономике при above_rec=False."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
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
    passes_rec_gate_for_up,
    shelf_rec_conversion_policy_active,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.test_auto_updater_v3 import _calc_kw

TS = datetime(2024, 1, 1, tzinfo=UTC)


def _policy_shelf() -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        aggressiveness=3,
    )


@pytest.mark.unit
def test_rec_gate_allows_min_blocks_opt_max_on_shelf_false() -> None:
    assert shelf_rec_conversion_policy_active(ShelfClickMode.SHELF_DOMINANT_OR_EQUAL)
    assert passes_rec_gate_for_up(
        False,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        to_mode=KeywordStrategyMode.MIN_CPA,
    )
    assert not passes_rec_gate_for_up(
        False,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        to_mode=KeywordStrategyMode.OPTIMUM,
    )
    assert not passes_rec_gate_for_up(
        False,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        to_mode=KeywordStrategyMode.MAX_CONVERSION,
    )


@pytest.mark.unit
def test_profitable_expansion_off_to_min_when_above_rec_false() -> None:
    """Кейс как adv 32824944: OFF, above_rec=False, M дешевле resolve → MIN."""
    prof = [
        PositionProfilePoint(
            position=1, bid=5340.0, predicted_conversion=0.13, pay_for_cart=1.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=49, bid=510.0, predicted_conversion=0.02, pay_for_cart=1.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(
        ks_id=200,
        text="крем для комбинированной кожи лица",
        mode=KeywordStrategyMode.OFF,
        rating=5.0,
        conv=0.01,
        hard_status=2,
        above_rec=False,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts(
        [ctx],
        rk_orders_per_cart=0.26,
        rec_orders_per_view=0.004,
    )
    actions = plan_profitable_expansion(
        prepared,
        resolve=120.0,
        policy=_policy_shelf(),
        ladder_inputs=ladder,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
