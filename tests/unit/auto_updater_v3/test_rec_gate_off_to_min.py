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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
    passes_rec_gate_for_up,
    shelf_rec_conversion_policy_active,
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
