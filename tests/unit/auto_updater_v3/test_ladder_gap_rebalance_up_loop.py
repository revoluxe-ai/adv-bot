"""Unit-тесты цикла N×UP в gap-rebalance."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rebalance import (
    plan_ladder_gap_rebalance,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)

from tests.unit.auto_updater_v3.conftest import calc_kw, sample_profile


@pytest.mark.unit
def test_plan_ladder_gap_rebalance_stops_up_loop_on_do_nothing() -> None:
    prof = sample_profile()
    prepared = [
        (
            KeywordV3Context(
                keyword=calc_kw(
                    ks_id=1,
                    text="a",
                    mode=KeywordStrategyMode.MIN_CPA,
                    hard_status=2,
                ),
                position_profile=prof,
            ),
            KeywordStrategyMode.MIN_CPA,
        ),
        (
            KeywordV3Context(
                keyword=calc_kw(
                    ks_id=2,
                    text="b",
                    mode=KeywordStrategyMode.OFF,
                    hard_status=2,
                ),
                position_profile=prof,
            ),
            KeywordStrategyMode.OFF,
        ),
        (
            KeywordV3Context(
                keyword=calc_kw(
                    ks_id=3,
                    text="c",
                    mode=KeywordStrategyMode.MAX_CONVERSION,
                    hard_status=2,
                ),
                position_profile=prof,
            ),
            KeywordStrategyMode.MAX_CONVERSION,
        ),
    ]
    up_calls = 0

    def fake_up(*_a: object, **_k: object) -> list[V3Action]:
        nonlocal up_calls
        up_calls += 1
        if up_calls <= 2:
            return [
                V3Action(
                    action=V3ActionType.UP,
                    keyword_setting_id=2,
                    target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                    reason="fake",
                )
            ]
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="no_up")]

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rebalance._plan_rebalance_up_once",
        side_effect=fake_up,
    ):
        actions = plan_ladder_gap_rebalance(
            prepared,
            shelf_promotion_active=False,
            shelf_click_mode=ShelfClickMode.UNKNOWN,
            rollout_aggressiveness=1,
        )

    assert sum(1 for a in actions if a.action == V3ActionType.FORCE_OFF) == 1
    assert sum(1 for a in actions if a.action == V3ActionType.UP) == 2
    assert up_calls == 3
