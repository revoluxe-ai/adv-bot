"""Unit: StepManager — UP/DOWN по ``UpdateContext`` и history."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared import (
    build_update_context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager import (
    StepCandidate,
    StepManager,
    run_step_down,
    run_steps_down,
)
from tests.unit.auto_updater_v3.test_effective_ladder_steps import _fake_catalog_places
from tests.unit.test_auto_updater_v3 import _calc_kw


def _ctx(ks_id: int, mode: KeywordStrategyMode) -> KeywordV3Context:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
    )
    return KeywordV3Context(keyword=kw, position_profile=None)


def _update_ctx(*specs: tuple[int, KeywordStrategyMode]):
    contexts = [_ctx(ks_id, mode) for ks_id, mode in specs]
    return build_update_context(contexts)


def _sort_key(c: StepCandidate) -> tuple[float, float, int]:
    return (-c.state_cost, -c.pay_for_order, c.keyword_setting_id)


@pytest.mark.unit
def test_run_step_down_picks_max_state_cost_and_records_history() -> None:
    ctx = _update_ctx((1, KeywordStrategyMode.MIN_CPA), (2, KeywordStrategyMode.MIN_CPA))
    result = run_step_down(
        ctx,
        collect=lambda _w: [
            StepCandidate(1, KeywordStrategyMode.MIN_CPA, KeywordStrategyMode.OPTIMUM, 10.0),
            StepCandidate(2, KeywordStrategyMode.MIN_CPA, KeywordStrategyMode.MAX_CONVERSION, 100.0),
        ],
        sort_key=_sort_key,
    )
    assert result.pick is not None
    assert result.pick.keyword_setting_id == 2
    assert result.context.prepared[1][1] == KeywordStrategyMode.MAX_CONVERSION
    dto = result.context.keywords[1]
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert [s.new_mode for s in dto.next_state] == [
        KeywordStrategyMode.MAX_CONVERSION,
    ]


@pytest.mark.unit
def test_run_steps_down_applies_budget_and_appends_history() -> None:
    ctx = _update_ctx((1, KeywordStrategyMode.MIN_CPA))
    step_targets = [KeywordStrategyMode.OPTIMUM, KeywordStrategyMode.MAX_CONVERSION]
    call = 0

    def collect(working_ctx) -> list[StepCandidate]:
        nonlocal call
        mode = working_ctx.prepared[0][1]
        if call >= len(step_targets):
            return []
        to_mode = step_targets[call]
        call += 1
        return [
            StepCandidate(
                1,
                mode,
                to_mode,
                state_cost=float(len(step_targets) - call),
            )
        ]

    batch = run_steps_down(ctx, 2, collect=collect, sort_key=_sort_key)
    assert len(batch.picks) == 2
    dto = batch.context.keywords[0]
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert [s.new_mode for s in dto.next_state] == [
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    ]


@pytest.mark.unit
def test_run_step_down_stops_on_empty_pool() -> None:
    result = run_step_down(
        _update_ctx((1, KeywordStrategyMode.MIN_CPA)),
        collect=lambda _w: [],
        sort_key=_sort_key,
    )
    assert result.pick is None
    assert result.pool_size == 0


@pytest.mark.unit
def test_step_manager_resolve_down_max_to_min_released_one() -> None:
    cat = _fake_catalog_places(min_place=40, opt_place=1, max_place=1)
    step = StepManager.resolve_down(KeywordStrategyMode.MAX_CONVERSION, cat)
    assert step.to_mode == KeywordStrategyMode.MIN_CPA
    assert step.released_aggression_steps == 1


@pytest.mark.unit
def test_step_manager_resolve_up_off_to_max_on_degenerate_catalog() -> None:
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    step = StepManager.resolve_up(KeywordStrategyMode.OFF, cat)
    assert step.to_mode == KeywordStrategyMode.MAX_CONVERSION
