"""Unit-тесты ``transition_ranking``: jump UP, state_cost, no-data imputation, rec-gate."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    RecTier,
    UpMoveKind,
    build_worst_per_state_costs,
    collect_transition_candidates,
    move_kind_for,
    pick_one_up_cost_first,
    plan_shelf_rec_false_cleanup_down,
    upper_target_modes,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from tests.unit.auto_updater_v3.conftest import calc_kw, ctx, sample_profile


@pytest.mark.unit
def test_upper_target_modes_from_off() -> None:
    modes = upper_target_modes(KeywordStrategyMode.OFF)
    assert modes == [
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    ]


@pytest.mark.unit
def test_upper_target_modes_from_c_empty() -> None:
    assert upper_target_modes(KeywordStrategyMode.MAX_CONVERSION) == []


@pytest.mark.unit
def test_move_kind_off_to_max() -> None:
    assert (
        move_kind_for(KeywordStrategyMode.OFF, KeywordStrategyMode.MAX_CONVERSION)
        == UpMoveKind.OFF_TO_MAX
    )


@pytest.mark.unit
def test_jump_off_collects_multiple_targets() -> None:
    prof = sample_profile(min_pay=10.0, high_pay=15.0)
    prepared = [
        (ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=prof), KeywordStrategyMode.OFF, True)
    ]
    candidates = collect_transition_candidates(
        prepared,
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
    )
    kinds = {c.move_kind for c in candidates}
    assert UpMoveKind.OFF_TO_MIN in kinds
    assert UpMoveKind.OFF_TO_MAX in kinds


@pytest.mark.unit
def test_rec_gate_blocks_false_on_shelf() -> None:
    prof = sample_profile()
    prepared = [
        (
            ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=prof, above_rec=False),
            KeywordStrategyMode.OFF,
            False,
        )
    ]
    candidates = collect_transition_candidates(
        prepared,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
    )
    assert candidates == []


@pytest.mark.unit
def test_no_data_provisional_imputed_uses_worst() -> None:
    data_prof = sample_profile(min_pay=20.0, high_pay=30.0)
    prepared = [
        (
            ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=data_prof, above_rec=True),
            KeywordStrategyMode.OFF,
            False,
        ),
        (
            ctx(ks_id=2, mode=KeywordStrategyMode.OFF, profile=None, above_rec=None),
            KeywordStrategyMode.OFF,
            False,
        ),
    ]
    worst = build_worst_per_state_costs(prepared)
    assert AggressionTargetMode.MIN_CPA in worst
    candidates = collect_transition_candidates(
        prepared,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
    )
    imputed = [c for c in candidates if c.rec_tier == RecTier.PROVISIONAL_IMPUTED]
    assert len(imputed) >= 1
    assert any(c.imputed for c in imputed)


@pytest.mark.unit
def test_no_target_place_data_is_treated_as_no_data() -> None:
    data_prof = sample_profile(min_pay=20.0, high_pay=30.0)
    prepared = [
        (
            ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=data_prof, above_rec=True),
            KeywordStrategyMode.OFF,
            True,
        ),
        (
            ctx(ks_id=2, mode=KeywordStrategyMode.OFF, profile=None, above_rec=True),
            KeywordStrategyMode.OFF,
            False,
        ),
    ]
    candidates = collect_transition_candidates(
        prepared,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
    )
    assert any(
        c.ctx.keyword.keyword_setting_original_id == 2
        and c.to_mode == KeywordStrategyMode.MAX_CONVERSION
        and c.imputed
        for c in candidates
    )


@pytest.mark.unit
def test_confirmed_tier_before_imputed() -> None:
    prof_cheap = sample_profile(min_pay=5.0, high_pay=6.0)
    prof_expensive = sample_profile(min_pay=100.0, high_pay=200.0)
    prepared = [
        (
            ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=prof_expensive, above_rec=None),
            KeywordStrategyMode.OFF,
            False,
        ),
        (
            ctx(ks_id=2, mode=KeywordStrategyMode.OFF, profile=prof_cheap, above_rec=True),
            KeywordStrategyMode.OFF,
            False,
        ),
    ]
    candidates = collect_transition_candidates(
        prepared,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
    )
    action = pick_one_up_cost_first(candidates, reason_prefix="test")
    assert action is not None
    assert action.keyword_setting_id == 2


@pytest.mark.unit
def test_shelf_false_cleanup_down_active() -> None:
    prof = sample_profile()
    base = calc_kw(
        ks_id=1,
        text="bad",
        mode=KeywordStrategyMode.MIN_CPA,
        hard_status=2,
        above_rec=False,
    )
    ks_dto = base.keyword_setting.model_copy(update={"hard_status": 2})
    kw = base.model_copy(update={"keyword_setting": ks_dto})
    prepared = [
        (KeywordV3Context(keyword=kw, position_profile=prof), KeywordStrategyMode.MIN_CPA, True)
    ]
    actions = plan_shelf_rec_false_cleanup_down(
        prepared,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
    )
    assert actions is not None
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].reason == "shelf_rec_false_cleanup"


@pytest.mark.unit
def test_plan_cost_first_up_one_sets_selection_log() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
        V3RolloutAggressiveness,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        plan_cost_first_up_one,
    )

    prof = sample_profile(min_pay=10.0, high_pay=15.0)
    prepared = [
        (ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=prof), KeywordStrategyMode.OFF, False)
    ]
    actions = plan_cost_first_up_one(
        prepared,
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        layered=False,
        aggressiveness=V3RolloutAggressiveness.MAX,
        piecewise_shelf=False,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    log = actions[0].selection_log
    assert log is not None
    assert log.pool_size == 1
    assert log.state_cost is not None
    assert log.from_mode == "OFF"
