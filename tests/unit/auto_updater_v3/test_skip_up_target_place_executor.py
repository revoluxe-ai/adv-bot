"""Unit: skip_up_same_target_place executor, NSM и resolver."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    resolve_alias_collapse_up_at_same_target_place,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    KeywordDTO,
    UpdateContextManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordsPreparedList,
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
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.skip_up_target_place import (
    SkipUpTargetPlaceExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from tests.unit.test_auto_updater_v3 import _calc_kw, _sample_profile


def _fake_catalog_places(
    *,
    min_place: int,
    opt_place: int,
    max_place: int,
) -> dict[AggressionTargetMode, ModeCandidate]:
    def _mc(mode: AggressionTargetMode, place: int) -> ModeCandidate:
        return ModeCandidate(
            mode=mode,
            position=place,
            bid=500.0,
            predicted_cpa=100.0,
            is_valid=True,
        )

    return {
        AggressionTargetMode.MIN_CPA: _mc(AggressionTargetMode.MIN_CPA, min_place),
        AggressionTargetMode.OPTIMUM: _mc(AggressionTargetMode.OPTIMUM, opt_place),
        AggressionTargetMode.MAX_CONVERSION: _mc(
            AggressionTargetMode.MAX_CONVERSION, max_place
        ),
    }


def _ladder_states_alias(
    ks_id: int,
    *,
    place: int = 40,
) -> tuple[KeywordV3LadderState, ...]:
    return (
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MIN_CPA,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            target_position=place,
            cpo=300.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=place,
            cpo=400.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MAX_CONVERSION,
            strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
            target_position=place,
            cpo=600.0,
        ),
    )


def _ladder_states_distinct_places(ks_id: int) -> tuple[KeywordV3LadderState, ...]:
    return (
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MIN_CPA,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            target_position=10,
            cpo=300.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=20,
            cpo=400.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MAX_CONVERSION,
            strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
            target_position=30,
            cpo=600.0,
        ),
    )


def _dto(
    *,
    ks_id: int = 1,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    ladder: tuple[KeywordV3LadderState, ...] | None = None,
) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=_sample_profile())
    states = ladder if ladder is not None else _ladder_states_alias(ks_id)
    return KeywordDTO.from_context(ctx, ladder_states=states)


@pytest.mark.unit
def test_resolver_alias_same_place_collapses_to_max() -> None:
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=40)
    assert (
        resolve_alias_collapse_up_at_same_target_place(
            KeywordStrategyMode.MIN_CPA, cat
        )
        == KeywordStrategyMode.MAX_CONVERSION
    )


@pytest.mark.unit
def test_resolver_noop_when_next_step_changes_place() -> None:
    cat = _fake_catalog_places(min_place=10, opt_place=20, max_place=30)
    assert (
        resolve_alias_collapse_up_at_same_target_place(
            KeywordStrategyMode.MIN_CPA, cat
        )
        is None
    )


@pytest.mark.unit
def test_resolver_noop_for_off_and_max() -> None:
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=40)
    assert (
        resolve_alias_collapse_up_at_same_target_place(KeywordStrategyMode.OFF, cat)
        is None
    )
    assert (
        resolve_alias_collapse_up_at_same_target_place(
            KeywordStrategyMode.MAX_CONVERSION, cat
        )
        is None
    )


@pytest.mark.unit
def test_nsm_skip_up_applies_max_on_alias_group() -> None:
    nsm = NextStateManager(SkipUpTargetPlaceExecutor)
    dto = _dto(mode=KeywordStrategyMode.MIN_CPA)
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=40)
    nsm.skip_up_same_target_place(dto, cat)
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert dto.target_place == 40
    assert dto.next_state[-1].executor_name == "SkipUpTargetPlaceExecutor"


@pytest.mark.unit
def test_nsm_skip_up_noop_when_no_alias() -> None:
    nsm = NextStateManager(SkipUpTargetPlaceExecutor)
    dto = _dto(
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states_distinct_places(1),
    )
    cat = _fake_catalog_places(min_place=10, opt_place=20, max_place=30)
    nsm.skip_up_same_target_place(dto, cat)
    assert dto.next_state == []
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_skip_up_executor_mutates_only_alias_keywords() -> None:
    dto_alias = _dto(ks_id=1, mode=KeywordStrategyMode.MIN_CPA)
    dto_distinct = _dto(
        ks_id=2,
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states_distinct_places(2),
    )
    adv_state = replace(AdvState.empty(), resolve=500.0)
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto_alias, dto_distinct]),
        adv_state=adv_state,
    )
    alias_cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=40)
    distinct_cat = _fake_catalog_places(min_place=10, opt_place=20, max_place=30)

    def _catalog_side_effect(ctx: KeywordV3Context, _ladder_inputs: object) -> dict:
        if ctx.keyword.keyword_setting.id == 1:
            return alias_cat
        return distinct_cat

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.skip_up_target_place.state_candidates_by_mode_for_ctx",
        side_effect=_catalog_side_effect,
    ):
        SkipUpTargetPlaceExecutor().execute(ctx)

    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert ctx.keywords[1].next_state == []


@pytest.mark.unit
def test_skip_up_executor_in_preamble() -> None:
    executors = build_normal_preamble_executors()
    assert executors[2].phase_name == "skip_up_same_target_place"
    assert executors[3].phase_name == "raise_state_to_target_cpo"
