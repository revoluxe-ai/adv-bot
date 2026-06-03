"""Дебаг-прогон: цепочка resolver ×2 и planner CAL UP/DOWN (пишет debug-de9fc0.log)."""

from __future__ import annotations

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_resolve_calibration,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_debug_agent_log import (
    v3_agent_debug_log,
)
from tests.unit.auto_updater_v3.test_calibration_adaptive_integration import (
    _patch_ladder_costs,
    _three_place_profile,
)
from tests.unit.auto_updater_v3.test_calibration_adaptive_integration import (
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from tests.unit.test_auto_updater_v3 import (
    _calc_kw,
    _conv_for_pay_for_order,
)


@pytest.mark.unit
def test_debug_run_resolver_chain_loosen_cap8(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Симуляция 5 тиков UP: бюджет 1→2→4→8→8 (cap)."""
    cap = 8
    prev: CalibrationStepState | None = None
    for tick in range(1, 6):
        budget = resolve_effective_calibration_steps(
            cap,
            prev=prev,
            current_direct=CalibrationDirect.LOOSEN,
        )
        v3_agent_debug_log(
            location="test_calibration_debug_run.py:resolver_chain",
            message="simulated_tick",
            hypothesis_id="H-chain",
            run_id="debug-run",
            data={
                "tick": tick,
                "budget": budget,
                "prev_steps": prev.effective_steps if prev else None,
                "prev_direct": prev.direct.value if prev else None,
            },
        )
        prev = CalibrationStepState(
            effective_steps=budget,
            direct=CalibrationDirect.LOOSEN,
        )
    assert prev is not None
    assert prev.effective_steps == cap


@pytest.mark.unit
def test_debug_run_flip_loosen_to_tighten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Разворот UP@8 → DOWN@4."""
    prev = CalibrationStepState(8, CalibrationDirect.LOOSEN)
    down = resolve_effective_calibration_steps(
        8, prev=prev, current_direct=CalibrationDirect.TIGHTEN
    )
    v3_agent_debug_log(
        location="test_calibration_debug_run.py:flip",
        message="loosen_to_tighten",
        hypothesis_id="H-flip",
        run_id="debug-run",
        data={"prev_steps": 8, "budget_down": down},
    )
    assert down == 4


@pytest.mark.unit
def test_debug_run_planner_budgets_match_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Planner: budget 1/2/4 → actions_count совпадает (один ключ MIN)."""
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
        text="debug_chain",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(10.0),
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=_three_place_profile())]
    )
    for budget in (1, 2, 4):
        actions = plan_resolve_calibration(
            prepared,
            resolve=550.0,
            calibration_direct=CalibrationDirect.LOOSEN,
            shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
            aggressiveness=V3RolloutAggressiveness.MAX,
            max_effective_steps=budget,
        )
        v3_agent_debug_log(
            location="test_calibration_debug_run.py:planner",
            message="budget_vs_actions",
            hypothesis_id="H-planner",
            run_id="debug-run",
            data={"budget": budget, "actions_count": len(actions)},
        )
        assert len(actions) == min(budget, 2)
        assert len(actions) <= budget
