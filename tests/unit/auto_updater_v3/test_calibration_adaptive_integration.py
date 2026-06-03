"""Интеграция: ``resolve_effective_calibration_steps`` → ``plan_resolve_calibration`` (UP/DOWN).

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_resolve_calibration,
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
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
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
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
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

    actions_one = plan_resolve_calibration(
        prepared,
        resolve=550.0,
        calibration_direct=CalibrationDirect.LOOSEN,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=1,
    )
    actions_two = plan_resolve_calibration(
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
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
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
    actions = plan_resolve_calibration(
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
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
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
    actions = plan_resolve_calibration(
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
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=_three_place_profile())]
    )
    prev = CalibrationStepState(1, CalibrationDirect.TIGHTEN)
    budget = resolve_effective_calibration_steps(
        10, prev=prev, current_direct=CalibrationDirect.TIGHTEN
    )
    assert budget == 2

    one = plan_resolve_calibration(
        prepared,
        resolve=300.0,
        calibration_direct=CalibrationDirect.TIGHTEN,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=1,
    )
    two = plan_resolve_calibration(
        prepared,
        resolve=300.0,
        calibration_direct=CalibrationDirect.TIGHTEN,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        max_effective_steps=budget,
    )
    assert len(one) == 1
    assert one[0].target_strategy_mode == KeywordStrategyMode.OPTIMUM
    assert len(two) == 2
    assert two[0].target_strategy_mode == KeywordStrategyMode.OPTIMUM
    assert two[1].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert mode_level(two[1].target_strategy_mode) < mode_level(
        two[0].target_strategy_mode
    )
    assert one[0].action in (V3ActionType.DOWN, V3ActionType.FORCE_OFF)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_up_branch_passes_resolver_budget_to_real_planner() -> None:
    """UP-тик: orchestrator не мокает planner; ``max_effective_steps`` из resolver."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
        CalibrationStepState,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
        process_adv_v3,
    )
    from tests.unit.auto_updater_v3.test_orchestrator_overspend_gate import (
        _fact_for_cpa_gates,
        _plan_for_cpa_gates,
    )

    plan = _plan_for_cpa_gates()
    fact = _fact_for_cpa_gates(pay_for_order=50.0)

    complex_adv = MagicMock()
    complex_adv.adv_id = 99
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 3
    complex_adv.keyword_calibration_max_step = 10
    complex_adv.get_keywords = AsyncMock(return_value=[])

    prev_state = CalibrationStepState(
        effective_steps=1,
        direct=CalibrationDirect.LOOSEN,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(MagicMock(), {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cap_down.plan_mode_cap_down",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.passing_up.plan_passing_up",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation.plan_cost_reallocation",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable.plan_pay_for_order_gap_enable",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFact"
        ) as pfc_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFactViews"
        ) as views_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_complex_adv_total_views",
            new=AsyncMock(return_value=200),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState"
        ) as step_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration.plan_resolve_calibration",
            wraps=plan_resolve_calibration,
        ) as calibration_spy,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
    ):
        plan_fact = MagicMock()
        plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
        plan_fact.set_new_plan_fact = AsyncMock()
        pfc_cls.return_value = plan_fact
        views_cls.return_value.get_cached_views = AsyncMock(return_value=100)
        views_cls.return_value.set_views = AsyncMock()
        step_mock = step_cls.return_value
        step_mock.get_state = AsyncMock(return_value=prev_state)
        step_mock.set_state = AsyncMock()
        updater_cls.get_plan_data.return_value = plan
        updater_cls.return_value.get_fact_data = AsyncMock(return_value=fact)

        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    calibration_spy.assert_called_once()
    assert calibration_spy.call_args.kwargs.get("max_effective_steps") == 2
    assert (
        calibration_spy.call_args.kwargs.get("calibration_direct")
        == CalibrationDirect.LOOSEN
    )
