"""Unit-тесты ``transition_ranking``: pooled UP, rec-gate и aggr-фильтр."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    RecTier,
    SelectionPolicy,
    UpMoveKind,
    build_worst_per_state_costs,
    collect_transition_candidates,
    missing_above_rec,
    missing_target_matrix,
    missing_target_matrix_from_catalog,
    move_kind_for,
    pick_one_up_cost_first,
    plan_one_up_by_policy,
    plan_shelf_rec_false_cleanup_down,
    upper_target_modes,
)
from tests.unit.auto_updater_v3.conftest import calc_kw, ctx, sample_profile


def _policy(
    *,
    click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness = V3RolloutAggressiveness.MAX,
) -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=click_mode,
        aggressiveness=aggressiveness,
    )


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
        (ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=prof), KeywordStrategyMode.OFF)
    ]
    candidates = collect_transition_candidates(
        prepared,
        policy=_policy(click_mode=ShelfClickMode.ORGANIC_DOMINANT),
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
        )
    ]
    candidates = collect_transition_candidates(
        prepared,
        policy=_policy(click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL),
    )
    assert candidates == []


@pytest.mark.unit
def test_missing_above_rec_allows_full_jump_on_shelf() -> None:
    """missing_above_rec -> tier ниже confirmed, jump по pooled-стоимости."""
    prof = sample_profile(min_pay=10.0, high_pay=15.0)
    kw_ctx = ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=prof, above_rec=None)
    assert missing_above_rec(kw_ctx)
    prepared = [(kw_ctx, KeywordStrategyMode.OFF)]
    candidates = collect_transition_candidates(
        prepared,
        policy=_policy(click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL),
    )
    assert candidates
    assert all(c.rec_tier == RecTier.MISSING_ABOVE_REC for c in candidates)
    assert any(c.to_mode == KeywordStrategyMode.MAX_CONVERSION for c in candidates)


@pytest.mark.unit
def test_missing_target_matrix_imputed_uses_worst() -> None:
    data_prof = sample_profile(min_pay=20.0, high_pay=30.0)
    no_matrix = ctx(ks_id=2, mode=KeywordStrategyMode.OFF, profile=None, above_rec=None)
    prepared = [
        (
            ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=data_prof, above_rec=True),
            KeywordStrategyMode.OFF,
        ),
        (no_matrix, KeywordStrategyMode.OFF),
    ]
    assert missing_target_matrix(no_matrix)
    empty_catalog = build_mode_candidates(
        profile=None,
        keyword_text=no_matrix.keyword.text,
        conv_views_to_orders=no_matrix.keyword.conv_views_to_orders,
    )
    assert missing_target_matrix_from_catalog(empty_catalog)
    worst = build_worst_per_state_costs(prepared)
    assert AggressionTargetMode.MIN_CPA in worst
    candidates = collect_transition_candidates(
        prepared,
        policy=_policy(click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL),
    )
    imputed = [c for c in candidates if c.imputed]
    assert imputed


@pytest.mark.unit
def test_confirmed_tier_before_missing_above_rec() -> None:
    prof_cheap = sample_profile(min_pay=5.0, high_pay=6.0)
    prof_expensive = sample_profile(min_pay=100.0, high_pay=200.0)
    prepared = [
        (
            ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=prof_expensive, above_rec=None),
            KeywordStrategyMode.OFF,
        ),
        (
            ctx(ks_id=2, mode=KeywordStrategyMode.OFF, profile=prof_cheap, above_rec=True),
            KeywordStrategyMode.OFF,
        ),
    ]
    candidates = collect_transition_candidates(
        prepared,
        policy=_policy(click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL),
    )
    action = pick_one_up_cost_first(candidates)
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
    prepared = [(KeywordV3Context(keyword=kw, position_profile=prof), KeywordStrategyMode.MIN_CPA)]
    actions = plan_shelf_rec_false_cleanup_down(
        prepared,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].reason == "shelf_rec_false_cleanup"
    assert actions[0].target_strategy_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_shelf_false_cleanup_down_active_when_traffic_unknown() -> None:
    """UNKNOWN (нет traffic DTO) — тот же триггер полочного правила, что и rec-gate на UP."""
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
    prepared = [(KeywordV3Context(keyword=kw, position_profile=prof), KeywordStrategyMode.MIN_CPA)]
    actions = plan_shelf_rec_false_cleanup_down(
        prepared,
        click_mode=ShelfClickMode.UNKNOWN,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN


@pytest.mark.unit
def test_shelf_false_cleanup_mass_all_above_rec_false() -> None:
    """За один тик — действие на каждый активный ключ с above_rec=False."""
    prof = sample_profile()
    prepared = [
        (
            ctx(
                ks_id=1,
                mode=KeywordStrategyMode.MIN_CPA,
                profile=prof,
                above_rec=False,
                hard_status=2,
            ),
            KeywordStrategyMode.MIN_CPA,
        ),
        (
            ctx(
                ks_id=2,
                mode=KeywordStrategyMode.OPTIMUM,
                profile=prof,
                above_rec=False,
                hard_status=2,
            ),
            KeywordStrategyMode.OPTIMUM,
        ),
        (
            ctx(
                ks_id=3,
                mode=KeywordStrategyMode.MIN_CPA,
                profile=prof,
                above_rec=True,
                hard_status=2,
            ),
            KeywordStrategyMode.MIN_CPA,
        ),
    ]
    actions = plan_shelf_rec_false_cleanup_down(
        prepared,
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
    )
    assert len(actions) == 2
    ids = {a.keyword_setting_id for a in actions}
    assert ids == {1, 2}


@pytest.mark.unit
def test_shelf_false_cleanup_auto_uses_force_off() -> None:
    """Авто (hard_status=1): FORCE_OFF, т.к. applier не применяет DOWN для авто."""
    prof = sample_profile()
    prepared = [
        (
            ctx(
                ks_id=10,
                mode=KeywordStrategyMode.MIN_CPA,
                profile=prof,
                above_rec=False,
                hard_status=1,
            ),
            KeywordStrategyMode.MIN_CPA,
        ),
    ]
    actions = plan_shelf_rec_false_cleanup_down(
        prepared,
        click_mode=ShelfClickMode.UNKNOWN,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.FORCE_OFF
    assert actions[0].keyword_setting_id == 10


@pytest.mark.unit
def test_shelf_false_cleanup_skipped_on_organic_dominant() -> None:
    prof = sample_profile()
    prepared = [
        (
            ctx(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, profile=prof, above_rec=False),
            KeywordStrategyMode.MIN_CPA,
        )
    ]
    assert (
        plan_shelf_rec_false_cleanup_down(
            prepared,
            click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        )
        == []
    )


@pytest.mark.unit
def test_plan_one_up_by_policy_sets_selection_log() -> None:
    prof = sample_profile(min_pay=10.0, high_pay=15.0)
    prepared = [(ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=prof), KeywordStrategyMode.OFF)]
    actions = plan_one_up_by_policy(
        prepared,
        policy=_policy(click_mode=ShelfClickMode.ORGANIC_DOMINANT),
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    log = actions[0].selection_log
    assert log is not None
    assert log.pool_size == 3
    assert log.state_cost is not None
    assert log.from_mode == "OFF"


@pytest.mark.unit
def test_collect_candidates_filters_by_aggr_target_cap() -> None:
    prof = sample_profile(min_pay=10.0, high_pay=15.0)
    prepared = [
        (ctx(ks_id=1, mode=KeywordStrategyMode.OFF, profile=prof), KeywordStrategyMode.OFF)
    ]
    candidates = collect_transition_candidates(
        prepared,
        policy=_policy(
            click_mode=ShelfClickMode.ORGANIC_DOMINANT,
            aggressiveness=V3RolloutAggressiveness.MIN,
        ),
    )
    assert candidates
    assert all(c.to_mode == KeywordStrategyMode.MIN_CPA for c in candidates)


@pytest.mark.unit
def test_collect_candidates_skips_invalid_target_without_keyword_fallback() -> None:
    """Если target-state invalid в непустой матрице, кандидат не создаётся из pay_for_order."""
    prof = [p.model_copy(update={"pay_for_cart": None}) for p in sample_profile()]
    prepared = [
        (ctx(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, profile=prof), KeywordStrategyMode.MIN_CPA)
    ]
    candidates = collect_transition_candidates(
        prepared,
        policy=_policy(click_mode=ShelfClickMode.ORGANIC_DOMINANT),
    )
    assert candidates
    assert all(c.to_mode != KeywordStrategyMode.OPTIMUM for c in candidates)
