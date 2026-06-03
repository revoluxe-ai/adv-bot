"""Unit: validate_not_full_state executor и NOT FULL DTO."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared import (
    KeywordDTO,
    NextState,
    NextTargetPlace,
    UpdateContextManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.keyword_mode import (
    KeywordMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.ladder_state_kind import (
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors import (
    NotFullValidateExecutor,
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _dto(
    *,
    ks_id: int = 1,
    mode: KeywordStrategyMode = KeywordStrategyMode.MAX_CONVERSION,
    position_profile: list[PositionProfilePoint] | None = None,
    target_place: int | None = 15,
) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
    )
    if target_place is not None:
        kw.keyword_setting.target_place = target_place
    ctx = KeywordV3Context(keyword=kw, position_profile=position_profile)
    states = (
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
    )
    dto = KeywordDTO.from_context(ctx, ladder_states=states)
    dto.current_target_place = NextTargetPlace(
        new_target_place=0 if target_place is None else int(target_place),
        executor_name="PrepareExecutor",
    )
    return dto


@pytest.mark.unit
def test_is_not_full_without_ch_profile() -> None:
    dto = _dto(position_profile=None)
    assert dto.is_not_full() is True


@pytest.mark.unit
def test_is_full_with_ch_profile() -> None:
    profile = [PositionProfilePoint(position=1, bid=100)]
    dto = _dto(position_profile=profile)
    assert dto.is_not_full() is False


@pytest.mark.unit
def test_validate_not_full_active_max_down_to_min_and_zero() -> None:
    dto = _dto(mode=KeywordStrategyMode.MAX_CONVERSION, target_place=15)
    dto.current_mode = NextState(
        new_mode=KeywordMode.NOT_FULL_ACTIVATE,
        executor_name="Test",
    )
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.current_target_place == 0
    assert len(dto.next_state) == 1
    assert dto.next_state[0].new_mode is KeywordMode.MIN_CPA


@pytest.mark.unit
def test_validate_not_full_off_no_op() -> None:
    dto = _dto(mode=KeywordStrategyMode.OFF, target_place=0)
    dto.current_mode = NextState(
        new_mode=KeywordMode.NOT_FULL_ACTIVATE,
        executor_name="Test",
    )
    assert dto.next_state == []


@pytest.mark.unit
def test_validate_full_profile_no_op() -> None:
    profile = [PositionProfilePoint(position=1, bid=100)]
    dto = _dto(
        mode=KeywordStrategyMode.MAX_CONVERSION,
        position_profile=profile,
        target_place=15,
    )
    dto.current_mode = NextState(
        new_mode=KeywordMode.NOT_FULL_ACTIVATE,
        executor_name="Test",
    )
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert dto.next_state == []


@pytest.mark.unit
def test_nsm_validate_not_full_state() -> None:
    nsm = NextStateManager(NotFullValidateExecutor)
    dto = _dto(mode=KeywordStrategyMode.OPTIMUM, target_place=5)
    nsm.validate_not_full_state(dto)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.current_target_place == 0


@pytest.mark.unit
def test_not_full_validate_executor_second_in_preamble() -> None:
    executors = build_normal_preamble_executors()
    assert executors[1].phase_name == "validate_not_full_state"


@pytest.mark.unit
def test_not_full_validate_executor_mutates_context() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
        AdvState,
        KeywordsPreparedList,
    )

    dto = _dto(mode=KeywordStrategyMode.MAX_CONVERSION, target_place=20)
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=AdvState.empty(),
    )
    NotFullValidateExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MIN_CPA
    assert ctx.keywords[0].current_target_place == 0
