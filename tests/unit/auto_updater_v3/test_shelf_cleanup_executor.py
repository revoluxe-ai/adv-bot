"""Unit: ShelfCleanupExecutor multi-step DOWN + UP compensation."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
    RecGateStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.shelf_cleanup import (
    ShelfCleanupExecutor,
    run_shelf_cleanup_down,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _ladder(ks_id: int) -> tuple[KeywordV3LadderState, ...]:
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
            cpo=100.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=20,
            cpo=200.0,
        ),
    )


def _shelf_context(*, hard_status: int = 2):
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
        KeywordDTO,
    )

    kw = _calc_kw(
        ks_id=1,
        text="kw",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        hard_status=hard_status,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    dto = KeywordDTO.from_context(ctx, ladder_states=_ladder(1))
    ladder = LadderInputs.from_contexts([ctx], rec_orders_per_view=0.005)
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    adv_state = replace(
        AdvState.empty(),
        shelf_active=True,
        shelf_click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        policy=policy,
        ladder_inputs=ladder,
    )
    update_ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=adv_state,
    )
    return update_ctx, dto


@pytest.mark.unit
def test_shelf_cleanup_multi_step_whitelist_opt_min_off() -> None:
    """Regression: OPT FAIL → MIN still FAIL → OFF в одном прогоне (≥2 шага)."""
    update_ctx, dto = _shelf_context(hard_status=2)

    def _status(
        _cats: dict,
        to_mode: KeywordStrategyMode,
        _policy: SelectionPolicy,
        **kwargs: object,
    ) -> RecGateStatus:
        _ = (_cats, _policy, kwargs)
        if to_mode in (KeywordStrategyMode.OPTIMUM, KeywordStrategyMode.MIN_CPA):
            return RecGateStatus.FAIL
        return RecGateStatus.PASS

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate.state_rec_gate_status_for_mode",
        side_effect=_status,
    ):
        budget = run_shelf_cleanup_down(
            update_ctx,
            click_mode=ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
            ladder_inputs=update_ctx.adv_state.ladder_inputs,
            policy=update_ctx.adv_state.policy,
            nsm=ShelfCleanupExecutor()._next_state_manager,
        )

    assert dto.current_mode == KeywordStrategyMode.OFF
    assert budget >= 2
    assert len(dto.next_state) >= 2


@pytest.mark.unit
def test_shelf_cleanup_runs_up_compensation_for_down_budget() -> None:
    update_ctx, _dto = _shelf_context(hard_status=2)

    def _status(
        _cats: dict,
        to_mode: KeywordStrategyMode,
        _policy: SelectionPolicy,
        **kwargs: object,
    ) -> RecGateStatus:
        _ = (_cats, _policy, kwargs)
        if to_mode in (KeywordStrategyMode.OPTIMUM, KeywordStrategyMode.MIN_CPA):
            return RecGateStatus.FAIL
        return RecGateStatus.PASS

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate.state_rec_gate_status_for_mode",
        side_effect=_status,
    ), patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.shelf_cleanup.run_potential_up_steps",
    ) as up_mock:
        ShelfCleanupExecutor().execute(update_ctx)

    up_mock.assert_called_once()
    assert up_mock.call_args.kwargs["max_steps"] >= 2
