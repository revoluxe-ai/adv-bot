"""Unit: validate_state_by_hard_status executor и NextState."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_mode import (
    KeywordMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    KeywordDTO,
    NextState,
    UpdateContextManager,
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors import (
    HardStatusValidateExecutor,
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    HARD_STATUS_AUTO_MODE,
    HARD_STATUS_WHITE_LIST,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _dto(
    *,
    ks_id: int = 1,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    hard_status: int = HARD_STATUS_AUTO_MODE,
) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=hard_status,
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
def test_empty_next_state_reads_stored_mode() -> None:
    dto = _dto(mode=KeywordStrategyMode.MIN_CPA)
    assert dto.next_state == []
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_current_mode_setter_appends_next_state() -> None:
    dto = _dto()
    dto.current_mode = NextState(
        new_mode=KeywordMode.OFF,
        executor_name="TestExecutor",
    )
    assert len(dto.next_state) == 1
    assert dto.current_mode == KeywordStrategyMode.OFF
    assert dto.next_state[0].executor_name == "TestExecutor"


@pytest.mark.unit
def test_nsm_validate_hs1_dedup_when_already_off() -> None:
    nsm = NextStateManager(HardStatusValidateExecutor)
    dto = _dto(mode=KeywordStrategyMode.MIN_CPA, hard_status=HARD_STATUS_AUTO_MODE)
    nsm.validate_state_by_hard_status(dto)
    assert len(dto.next_state) == 1
    assert dto.current_mode == KeywordStrategyMode.OFF
    nsm.validate_state_by_hard_status(dto)
    assert len(dto.next_state) == 1


@pytest.mark.unit
def test_nsm_validate_skips_non_auto() -> None:
    nsm = NextStateManager(HardStatusValidateExecutor)
    dto = _dto(hard_status=HARD_STATUS_WHITE_LIST)
    nsm.validate_state_by_hard_status(dto)
    assert dto.next_state == []


@pytest.mark.unit
def test_hard_status_validate_executor_first_in_preamble() -> None:
    executors = build_normal_preamble_executors()
    assert executors[0].phase_name == "validate_state_by_hard_status"


@pytest.mark.unit
def test_hard_status_validate_executor_mutates_context_in_place() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        AdvState,
        KeywordsPreparedList,
    )

    dto = _dto(mode=KeywordStrategyMode.OPTIMUM, hard_status=HARD_STATUS_AUTO_MODE)
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=AdvState.empty(),
    )
    executor = HardStatusValidateExecutor()
    executor.execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.OFF
    assert ctx.keywords[0].next_state[-1].executor_name == "HardStatusValidateExecutor"
