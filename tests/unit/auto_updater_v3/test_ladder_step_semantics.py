"""Unit: SSOT классификации ladder-шагов (place / OFF / alias)."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    LadderStepKind,
    LadderStepSnapshot,
    classify_ladder_step,
    count_ladder_step_if_applied,
    is_ladder_step,
    ladder_step_snapshot_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _dto_with_ladder(
    *,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
) -> KeywordDTO:
    kw = _calc_kw(ks_id=1, text="kw", mode=mode, rating=1.0, hard_status=2)
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    states = (
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.MIN_CPA,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            target_position=10,
            cpo=100.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=20,
            cpo=200.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.MAX_CONVERSION,
            strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
            target_position=30,
            cpo=300.0,
        ),
    )
    return KeywordDTO.from_context(ctx, ladder_states=states)


@pytest.mark.unit
def test_same_target_place_alias_is_not_a_step() -> None:
    before = LadderStepSnapshot(KeywordStrategyMode.MIN_CPA, 10)
    after = LadderStepSnapshot(KeywordStrategyMode.OPTIMUM, 10)
    assert classify_ladder_step(before, after) is None
    assert count_ladder_step_if_applied(before, after) == 0


@pytest.mark.unit
def test_target_place_change_is_down_step() -> None:
    before = ladder_step_snapshot_for_mode(
        _dto_with_ladder(mode=KeywordStrategyMode.OPTIMUM),
        KeywordStrategyMode.OPTIMUM,
    )
    after = ladder_step_snapshot_for_mode(
        _dto_with_ladder(mode=KeywordStrategyMode.OPTIMUM),
        KeywordStrategyMode.MIN_CPA,
    )
    assert classify_ladder_step(before, after) == LadderStepKind.DOWN
    assert is_ladder_step(before, after)


@pytest.mark.unit
def test_off_transition_is_one_step() -> None:
    before = LadderStepSnapshot(KeywordStrategyMode.MIN_CPA, 10)
    after = LadderStepSnapshot(KeywordStrategyMode.OFF, None)
    assert classify_ladder_step(before, after) == LadderStepKind.OFF


@pytest.mark.unit
def test_off_to_active_is_up_step() -> None:
    before = LadderStepSnapshot(KeywordStrategyMode.OFF, None)
    after = LadderStepSnapshot(KeywordStrategyMode.MIN_CPA, 10)
    assert classify_ladder_step(before, after) == LadderStepKind.UP
