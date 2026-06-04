"""Unit: RebalanceExecutor, StatesListGenerator и ladder rebalance helpers."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors import (
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation import (
    RebalanceExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    pick_effective_down_ladder_state,
    resolve_current_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.states_list_generator import (
    StatesListGenerator,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _ladder_states(
    ks_id: int,
    *,
    min_cpo: float | None = 300.0,
    opt_cpo: float | None = 400.0,
    max_cpo: float | None = 600.0,
    min_place: int = 10,
    opt_place: int = 20,
    max_place: int = 30,
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
            target_position=min_place,
            cpo=min_cpo,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=opt_place,
            cpo=opt_cpo,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MAX_CONVERSION,
            strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
            target_position=max_place,
            cpo=max_cpo,
        ),
    )


def _alias_ladder_states(ks_id: int) -> tuple[KeywordV3LadderState, ...]:
    """M/O/C на place=20, MIN на place=10 — для теста skip alias при DOWN."""
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
            stage=V3LadderStageKind.MIN_CPA,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            target_position=20,
            cpo=400.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=20,
            cpo=410.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MAX_CONVERSION,
            strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
            target_position=20,
            cpo=500.0,
        ),
    )


def _dto(
    *,
    ks_id: int = 1,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    ladder: tuple[KeywordV3LadderState, ...] | None = None,
    hard_status: int = 2,
    target_place: int | None = None,
) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=hard_status,
    )
    states = ladder if ladder is not None else _ladder_states(ks_id)
    if target_place is None:
        for state in states:
            if state.strategy_mode == mode and state.cpo is not None:
                target_place = int(state.target_position)
                break
    if target_place is not None:
        kw.keyword_setting.target_place = target_place
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    return KeywordDTO.from_context(ctx, ladder_states=states)


def _adv_state(**overrides: object) -> AdvState:
    base = replace(
        AdvState.empty(),
        resolve=550.0,
        resolve_valid=True,
        max_pay_for_order=550.0,
    )
    return replace(base, **overrides)


@pytest.mark.unit
def test_generator_list1_active_modes_only() -> None:
    active = _dto(ks_id=1, mode=KeywordStrategyMode.MAX_CONVERSION)
    off = _dto(ks_id=2, mode=KeywordStrategyMode.OFF)
    no_cpo = _dto(
        ks_id=3,
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states(3, min_cpo=None, opt_cpo=None, max_cpo=None),
    )
    gen = StatesListGenerator(_adv_state())
    current, potential = gen.get_current_states([active, off, no_cpo])
    assert len(current) == 1
    assert current[0][0].keyword_setting_id == 1
    assert current[0][2] == 600.0
    assert len(potential) >= 1


@pytest.mark.unit
def test_generator_list2_only_states_above_current() -> None:
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.MIN_CPA)
    adv = _adv_state(
        policy=SelectionPolicy.from_aggressiveness(
            click_mode=ShelfClickMode.ORGANIC_DOMINANT,
            aggressiveness=V3RolloutAggressiveness.MAX,
        ),
    )
    gen = StatesListGenerator(adv)
    _current, potential = gen.get_current_states([dto])
    modes = {state.strategy_mode for _dto, state, _cpo in potential}
    assert KeywordStrategyMode.OPTIMUM in modes
    assert KeywordStrategyMode.MAX_CONVERSION in modes
    assert KeywordStrategyMode.MIN_CPA not in modes


@pytest.mark.unit
def test_generator_list2_off_keyword_has_min_potential() -> None:
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.OFF, target_place=0)
    gen = StatesListGenerator(_adv_state())
    _current, potential = gen.get_current_states([dto])
    assert any(
        item[0].keyword_setting_id == 1
        and item[1].strategy_mode == KeywordStrategyMode.MIN_CPA
        for item in potential
    )


@pytest.mark.unit
def test_shelf_filter_excludes_when_rec_baseline_missing() -> None:
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.MAX_CONVERSION)
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    adv = _adv_state(
        shelf_active=True,
        shelf_click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        policy=policy,
        ladder_inputs=LadderInputs.from_contexts([], rec_orders_per_view=None),
    )
    gen = StatesListGenerator(adv)
    current, potential = gen.get_current_states([dto])
    assert current == []
    assert potential == []


@pytest.mark.unit
def test_shelf_filter_not_applied_when_organic() -> None:
    active = _dto(ks_id=1, mode=KeywordStrategyMode.MAX_CONVERSION)
    off = _dto(ks_id=2, mode=KeywordStrategyMode.OFF, target_place=0)
    adv = _adv_state(shelf_active=True)
    gen = StatesListGenerator(adv)
    current, potential = gen.get_current_states([active, off])
    assert len(current) == 1
    assert len(potential) >= 1


@pytest.mark.unit
def test_rebalance_gate_skips_when_donor_not_more_expensive() -> None:
    expensive = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.OPTIMUM,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=400.0, max_cpo=500.0),
    )
    cheap_off = _dto(
        ks_id=2,
        mode=KeywordStrategyMode.OFF,
        target_place=0,
        ladder=_ladder_states(2, min_cpo=450.0, opt_cpo=500.0, max_cpo=550.0),
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[expensive, cheap_off]),
        adv_state=_adv_state(),
    )
    RebalanceExecutor().execute(ctx)
    assert ctx.keywords[0].next_state == []
    assert ctx.keywords[1].next_state == []


@pytest.mark.unit
def test_rebalance_one_cycle_down_donor_up_recipient() -> None:
    donor = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=250.0, opt_cpo=400.0, max_cpo=600.0),
    )
    recipient = _dto(
        ks_id=2,
        mode=KeywordStrategyMode.OFF,
        target_place=0,
        ladder=_ladder_states(2, min_cpo=450.0, opt_cpo=500.0, max_cpo=550.0),
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[donor, recipient]),
        adv_state=_adv_state(),
    )
    RebalanceExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.OPTIMUM
    assert ctx.keywords[1].current_mode == KeywordStrategyMode.MIN_CPA
    assert len(ctx.keywords[0].next_state) == 1
    assert len(ctx.keywords[1].next_state) == 1


@pytest.mark.unit
def test_pick_effective_down_skips_alias_same_target_place() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_alias_ladder_states(1),
        target_place=20,
    )
    down = pick_effective_down_ladder_state(dto)
    assert down is not None
    assert down.strategy_mode == KeywordStrategyMode.MIN_CPA
    assert down.target_position == 10
    assert down.cpo == 300.0


@pytest.mark.unit
def test_resolve_current_ladder_state_matches_target_place() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_alias_ladder_states(1),
        target_place=20,
    )
    state = resolve_current_ladder_state(dto)
    assert state is not None
    assert state.strategy_mode == KeywordStrategyMode.MAX_CONVERSION
    assert state.target_position == 20


@pytest.mark.unit
def test_rebalance_executor_skips_on_resolve_invalid() -> None:
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[_dto()]),
        adv_state=_adv_state(resolve_valid=False),
    )
    executor = RebalanceExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "resolve_invalid"


@pytest.mark.unit
def test_rebalance_executor_in_preamble() -> None:
    phases = [e.phase_name for e in build_normal_preamble_executors()]
    assert "cost_reallocation" in phases
