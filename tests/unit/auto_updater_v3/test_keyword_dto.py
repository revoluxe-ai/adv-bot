"""Unit: KeywordDTO и KeywordBatch."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    KeywordBatch,
    KeywordDTO,
    NextState,
    UpdateContextManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_mode import (
    KeywordMode,
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


def _dto(ks_id: int = 1) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    states = (
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
    )
    return KeywordDTO.from_context(ctx, ladder_states=states)


@pytest.mark.unit
def test_keyword_dto_tracks_next_state() -> None:
    dto = _dto()
    dto.current_mode = NextState(
        new_mode=KeywordMode.OPTIMUM,
        executor_name="Test",
    )
    assert dto.current_mode == KeywordStrategyMode.OPTIMUM
    assert len(dto.next_state) == 1
    assert dto.stored_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_keyword_batch_iter_yields_current_mode() -> None:
    dto = _dto()
    dto.current_mode = NextState(
        new_mode=KeywordMode.OPTIMUM,
        executor_name="Test",
    )
    batch = KeywordBatch([dto])
    pairs = list(batch)
    assert pairs[0][1] == KeywordStrategyMode.OPTIMUM


@pytest.mark.unit
def test_update_context_exposes_keywords() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        AdvState,
        KeywordsPreparedList,
    )

    dto = _dto()
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=AdvState.empty(),
    )
    assert len(ctx.keywords) == 1
    assert ctx.keywords[0] is dto


@pytest.mark.unit
def test_apply_ladder_state_syncs_target_place() -> None:
    dto = _dto()
    state = KeywordV3LadderState(
        keyword_setting_id=1,
        stage=V3LadderStageKind.OPTIMUM,
        strategy_mode=KeywordStrategyMode.OPTIMUM,
        target_position=15,
        cpo=350.0,
    )
    dto.apply_ladder_state(state, executor_name="Test")
    assert dto.current_mode == KeywordStrategyMode.OPTIMUM
    assert dto.target_place == 15
