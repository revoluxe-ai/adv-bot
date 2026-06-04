"""Интеграция: ``resolve_effective_calibration_steps`` → calibration runner (UP/DOWN).

Проверяет, что бюджет adaptive steps из Redis-логики реально доходит до planner
и меняет глубину перехода на лестнице (не только kwargs в orchestrator-mock).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
    CalibrationStepState,
    resolve_effective_calibration_steps,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.calibration_runner import (
    plan_calibration_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration import (
    ResolveCalibrationExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    build_prepared_from_contexts,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.test_auto_updater_v3 import (
    _calc_kw,
    _conv_for_pay_for_order,
)


def _three_place_profile() -> list[PositionProfilePoint]:
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        PositionProfilePoint(
            position=1,
            bid=10_000.0,
            predicted_conversion=0.1,
            pay_for_cart=1.0,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=5,
            bid=2_000.0,
            predicted_conversion=0.05,
            pay_for_cart=1.0,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=22,
            bid=500.0,
            predicted_conversion=0.02,
            pay_for_cart=1.0,
            timestamp=ts,
        ),
    ]


def _moc_catalog() -> dict[AggressionTargetMode, ModeCandidate]:
    def _mc(mode: AggressionTargetMode, place: int) -> ModeCandidate:
        return ModeCandidate(
            mode=mode,
            position=place,
            bid=float(place * 100),
            predicted_cpa=100.0,
            is_valid=True,
        )

    return {
        AggressionTargetMode.MIN_CPA: _mc(AggressionTargetMode.MIN_CPA, 22),
        AggressionTargetMode.OPTIMUM: _mc(AggressionTargetMode.OPTIMUM, 5),
        AggressionTargetMode.MAX_CONVERSION: _mc(
            AggressionTargetMode.MAX_CONVERSION, 1
        ),
    }


def _patch_ladder_costs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    costs: dict[KeywordStrategyMode, tuple[float, bool]],
) -> None:
    catalog = _moc_catalog()

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder_tick_helpers.mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: catalog,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking._catalog_for_ctx",
        lambda _ctx, _prepared, ladder_inputs=None: catalog,
    )

    def _fake_cost(
        *,
        ctx: KeywordV3Context,
        to_mode: KeywordStrategyMode,
        **_: object,
    ) -> tuple[float, bool]:
        _ = ctx
        return costs.get(to_mode, (float("inf"), False))

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder_tick_helpers.resolve_effective_state_cost_for_mode",
        _fake_cost,
    )


@pytest.mark.unit
def test_resolver_second_up_tick_budget_is_two() -> None:
    """Второй тик ветки UP: Redis prev (1, UP) → бюджет 2."""
    prev = CalibrationStepState(
        effective_steps=1,
        direct=CalibrationDirect.LOOSEN,
    )
    budget = resolve_effective_calibration_steps(
        10,
        prev=prev,
        current_direct=CalibrationDirect.LOOSEN,
    )
    assert budget == 2


@pytest.mark.unit
def test_resolver_flip_down_to_up_halves_budget() -> None:
    """Разворот DOWN→UP: prev 8 → бюджет 4."""
    prev = CalibrationStepState(
        effective_steps=8,
        direct=CalibrationDirect.TIGHTEN,
    )
    budget = resolve_effective_calibration_steps(
        10,
        prev=prev,
        current_direct=CalibrationDirect.LOOSEN,
    )
    assert budget == 4


@pytest.mark.unit
def test_planner_up_uses_resolver_budget_second_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolver budget=2 → два итеративных UP на одном ключе (MIN→OPT, OPT→MAX)."""
    _patch_ladder_costs(
        monkeypatch,
        costs={
            KeywordStrategyMode.MIN_CPA: (10.0, False),
            KeywordStrategyMode.OPTIMUM: (25.0, False),
            KeywordStrategyMode.MAX_CONVERSION: (50.0, False),
        },
    )
    kw = _calc_kw(
        ks_id=14,
        text="resolver_planner_up",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(10.0),
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=_three_place_profile())]
    )
    prev = CalibrationStepState(1, CalibrationDirect.LOOSEN)
    budget = resolve_effective_calibration_steps(
        10, prev=prev, current_direct=CalibrationDirect.LOOSEN
    )
    assert budget == 2

    actions_one = plan_calibration_actions(
        prepared,
        resolve=550.0,
        calibration_direct=CalibrationDirect.LOOSEN,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=1,
    )
    actions_two = plan_calibration_actions(
        prepared,
        resolve=550.0,
        calibration_direct=CalibrationDirect.LOOSEN,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=budget,
    )
    assert len(actions_one) == 1
    assert actions_one[0].target_strategy_mode == KeywordStrategyMode.OPTIMUM
    assert len(actions_two) == 2
    assert actions_two[0].target_strategy_mode == KeywordStrategyMode.OPTIMUM
    assert actions_two[1].target_strategy_mode == KeywordStrategyMode.MAX_CONVERSION
    assert mode_level(actions_two[1].target_strategy_mode) > mode_level(
        actions_two[0].target_strategy_mode
    )


@pytest.mark.unit
def test_planner_up_iterative_picks_cheapest_each_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Бюджет 2: два UP на двух ключах с min state_cost первого шага (OFF→MIN)."""
    _patch_ladder_costs(
        monkeypatch,
        costs={
            KeywordStrategyMode.MIN_CPA: (10.0, False),
            KeywordStrategyMode.OPTIMUM: (25.0, False),
            KeywordStrategyMode.MAX_CONVERSION: (50.0, False),
        },
    )
    kw_cheap = _calc_kw(
        ks_id=101,
        text="cheap_off",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=_conv_for_pay_for_order(5.0),
        hard_status=2,
    )
    kw_dear = _calc_kw(
        ks_id=102,
        text="dear_off",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=_conv_for_pay_for_order(50.0),
        hard_status=2,
    )

    def _fake_cost(
        ctx: KeywordV3Context,
        to_mode: KeywordStrategyMode,
        **_: object,
    ) -> tuple[float, bool]:
        ks_id = ctx.keyword.keyword_setting_original_id
        base = {
            KeywordStrategyMode.MIN_CPA: (10.0, False),
            KeywordStrategyMode.OPTIMUM: (25.0, False),
            KeywordStrategyMode.MAX_CONVERSION: (50.0, False),
        }
        cost, imputed = base.get(to_mode, (float("inf"), False))
        if ks_id == 102 and to_mode == KeywordStrategyMode.MIN_CPA:
            return (30.0, imputed)
        return (cost, imputed)

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder_tick_helpers.resolve_effective_state_cost_for_mode",
        _fake_cost,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view.cost_for_mode",
        _fake_cost,
    )

    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=kw_cheap, position_profile=_three_place_profile()),
            KeywordV3Context(keyword=kw_dear, position_profile=_three_place_profile()),
        ]
    )
    actions = plan_calibration_actions(
        prepared,
        resolve=550.0,
        calibration_direct=CalibrationDirect.LOOSEN,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=2,
    )
    assert len(actions) == 2
    assert actions[0].keyword_setting_id == 101
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert actions[1].keyword_setting_id == 101
    assert actions[1].target_strategy_mode == KeywordStrategyMode.OPTIMUM


@pytest.mark.unit
def test_planner_down_iterative_picks_dearest_each_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CAL DOWN budget=2: два DOWN на двух ключах (дорогой state первым)."""
    _patch_ladder_costs(
        monkeypatch,
        costs={
            KeywordStrategyMode.MIN_CPA: (200.0, False),
            KeywordStrategyMode.OPTIMUM: (350.0, False),
            KeywordStrategyMode.MAX_CONVERSION: (500.0, False),
        },
    )

    def _fake_cost(
        *,
        ctx: KeywordV3Context,
        to_mode: KeywordStrategyMode,
        **_: object,
    ) -> tuple[float, bool]:
        ks_id = ctx.keyword.keyword_setting_original_id
        base = {
            KeywordStrategyMode.MIN_CPA: (200.0, False),
            KeywordStrategyMode.OPTIMUM: (350.0, False),
            KeywordStrategyMode.MAX_CONVERSION: (500.0, False),
        }
        cost, imputed = base.get(to_mode, (float("inf"), False))
        if ks_id == 201 and to_mode == KeywordStrategyMode.OPTIMUM:
            return (400.0, imputed)
        return (cost, imputed)

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder_tick_helpers.resolve_effective_state_cost_for_mode",
        _fake_cost,
    )

    kw_dear = _calc_kw(
        ks_id=201,
        text="dear_max",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=1.0,
        conv=_conv_for_pay_for_order(500.0),
        hard_status=2,
    )
    kw_cheap = _calc_kw(
        ks_id=202,
        text="cheap_max",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=1.0,
        conv=_conv_for_pay_for_order(300.0),
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=kw_dear, position_profile=_three_place_profile()),
            KeywordV3Context(keyword=kw_cheap, position_profile=_three_place_profile()),
        ]
    )
    actions = plan_calibration_actions(
        prepared,
        resolve=300.0,
        calibration_direct=CalibrationDirect.TIGHTEN,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=2,
    )
    assert len(actions) == 2
    assert actions[0].keyword_setting_id == 201
    assert actions[0].target_strategy_mode == KeywordStrategyMode.OPTIMUM
    assert actions[1].keyword_setting_id == 202
    assert actions[1].target_strategy_mode == KeywordStrategyMode.OPTIMUM


@pytest.mark.unit
def test_planner_down_uses_resolver_budget_doubled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CAL DOWN budget=2: два итеративных DOWN (MAX→OPT, OPT→MIN); budget=1 → MAX→OPT."""
    _patch_ladder_costs(
        monkeypatch,
        costs={
            KeywordStrategyMode.MAX_CONVERSION: (500.0, False),
            KeywordStrategyMode.OPTIMUM: (350.0, False),
            KeywordStrategyMode.MIN_CPA: (200.0, False),
        },
    )
    kw = _calc_kw(
        ks_id=13,
        text="resolver_planner_down",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=1.0,
        conv=_conv_for_pay_for_order(200.0),
        hard_status=2,
    )

    def _prepared():
        return build_prepared_from_contexts(
            [KeywordV3Context(keyword=kw, position_profile=_three_place_profile())]
        )

    prev = CalibrationStepState(1, CalibrationDirect.TIGHTEN)
    budget = resolve_effective_calibration_steps(
        10, prev=prev, current_direct=CalibrationDirect.TIGHTEN
    )
    assert budget == 2

    one = plan_calibration_actions(
        _prepared(),
        resolve=300.0,
        calibration_direct=CalibrationDirect.TIGHTEN,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=1,
    )
    two = plan_calibration_actions(
        _prepared(),
        resolve=300.0,
        calibration_direct=CalibrationDirect.TIGHTEN,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=budget,
    )
    assert len(one) == 1
    assert one[0].action in (V3ActionType.DOWN, V3ActionType.FORCE_OFF)
    assert len(two) == 2
    assert two[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert two[1].action == V3ActionType.FORCE_OFF
    assert one[0].action in (V3ActionType.DOWN, V3ActionType.FORCE_OFF)


@pytest.mark.unit
def test_orchestrator_up_branch_passes_resolver_budget_to_executor() -> None:
    """UP-тик: ``max_effective_steps`` из resolver попадает в ``AdvState`` executor."""
    from tests.unit.auto_updater_v3.test_resolve_calibration_executor import (
        _cal_adv_state,
        _ctx,
        _dto,
        _ladder_states,
    )

    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=400.0, max_cpo=600.0),
        target_place=10,
    )
    adv = _cal_adv_state(
        calibration_direct=CalibrationDirect.LOOSEN,
        max_effective_steps=2,
    )
    ctx = _ctx(dto, adv_state=adv)
    ResolveCalibrationExecutor().execute(ctx)
    assert len(ctx.keywords[0].next_state) == 2
