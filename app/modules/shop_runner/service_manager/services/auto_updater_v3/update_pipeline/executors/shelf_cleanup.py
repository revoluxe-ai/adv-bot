"""Фаза S: shelf rec-FAIL cleanup (multi-step DOWN) + UP-компенсация через list2."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    candidate_for_strategy_mode,
    count_ladder_step_if_applied,
    ladder_step_snapshot_from_dto,
    log_skipped_aliases,
    resolve_next_effective_step_down,
    target_place_from_mode_candidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    shelf_rec_conversion_policy_active,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.calibration_runner import (
    run_potential_up_steps,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    ladder_state_for_mode,
    ladder_state_for_mode_and_place,
    pick_off_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    HARD_STATUS_AUTO_MODE,
    HARD_STATUS_WHITE_LIST,
    is_v3_operable_hard_status,
)

logger = logging.getLogger(__name__)

_MAX_SHELF_CLEANUP_ITERATIONS_PER_KEY = 50


class ShelfCleanupExecutor:
    """SHELF_REC_CLEANUP: while rec-FAIL → DOWN/OFF; затем столько же UP из list2."""

    phase_name = "shelf_cleanup"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(ShelfCleanupExecutor)

    def execute(self, context: UpdateContext) -> None:
        state = context.adv_state
        if not state.shelf_active:
            self._skip_reason = "shelf_inactive"
            return
        self._skip_reason = None
        down_budget = run_shelf_cleanup_down(
            context,
            click_mode=state.shelf_click_mode,
            ladder_inputs=state.ladder_inputs,
            policy=state.policy,
            nsm=self._next_state_manager,
        )
        if down_budget > 0:
            run_potential_up_steps(
                context,
                max_steps=down_budget,
                nsm=self._next_state_manager,
            )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _apply_and_count_step(dto: KeywordDTO, mutator: Callable[[], None]) -> int:
    """Применить мутацию и вернуть ``1`` если SSOT зафиксировал ladder-шаг."""
    before = ladder_step_snapshot_from_dto(dto)
    mutator()
    after = ladder_step_snapshot_from_dto(dto)
    return count_ladder_step_if_applied(before, after)


def run_shelf_cleanup_down(
    context: UpdateContext,
    *,
    click_mode: ShelfClickMode,
    ladder_inputs: LadderInputs | None,
    policy: SelectionPolicy | None,
    nsm: NextStateManager,
) -> int:
    """Multi-step DOWN/OFF для rec-FAIL ключей; сумма ladder-шагов = бюджет UP."""
    if not shelf_rec_conversion_policy_active(click_mode):
        return 0

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder_tick_helpers import (
        ladder_inputs_for_prepared,
        mode_catalog_for_ctx,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
        rec_gate_allows_up,
        rec_gate_triggers_cleanup,
        state_rec_gate_status_for_mode,
    )

    prepared = context.prepared
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    gate_policy = policy or SelectionPolicy.from_aggressiveness(
        click_mode=click_mode,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    rec = ladder.rec_orders_per_view
    if rec is None:
        return 0

    down_budget = 0

    for dto in context.keywords:
        if dto.keyword_setting_id <= 0:
            continue
        if not is_v3_operable_hard_status(dto.hard_status):
            continue
        if dto.current_mode == KeywordStrategyMode.OFF:
            continue

        iterations = 0
        while iterations < _MAX_SHELF_CLEANUP_ITERATIONS_PER_KEY:
            iterations += 1
            catalog = mode_catalog_for_ctx(
                dto.context,
                prepared,
                ladder_inputs=ladder,
            )
            opc = ladder.orders_per_cart_for_ctx(dto.context)
            current_status = state_rec_gate_status_for_mode(
                catalog,
                dto.current_mode,
                gate_policy,
                rec_orders_per_view=rec,
                orders_per_cart=opc,
            )
            if not rec_gate_triggers_cleanup(current_status):
                break

            hard_status = int(dto.hard_status)
            ks_id = dto.keyword_setting_id

            if hard_status == HARD_STATUS_AUTO_MODE:
                off_state = pick_off_ladder_state(dto)
                if off_state is not None:
                    down_budget += _apply_and_count_step(
                        dto,
                        lambda s=off_state: nsm.raise_state_to_target_cpo(dto, s),
                    )
                else:
                    down_budget += _apply_and_count_step(dto, lambda: nsm.force_off(dto))
                break

            min_status = state_rec_gate_status_for_mode(
                catalog,
                KeywordStrategyMode.MIN_CPA,
                gate_policy,
                rec_orders_per_view=rec,
                orders_per_cart=opc,
            )

            if (
                rec_gate_allows_up(min_status)
                and dto.current_mode != KeywordStrategyMode.MIN_CPA
            ):
                min_state = ladder_state_for_mode(dto, KeywordStrategyMode.MIN_CPA)
                if min_state is None:
                    logger.warning(
                        "v3 shelf_rec_false_cleanup: whitelist ks_id=%s "
                        "MIN ladder missing; skip",
                        ks_id,
                    )
                    break
                down_budget += _apply_and_count_step(
                    dto,
                    lambda s=min_state: nsm.raise_state_to_target_cpo(dto, s),
                )
                continue

            if dto.current_mode == KeywordStrategyMode.MIN_CPA:
                off_state = pick_off_ladder_state(dto)
                if off_state is None:
                    logger.warning(
                        "v3 shelf_rec_false_cleanup: whitelist ks_id=%s at MIN, "
                        "OFF ladder missing",
                        ks_id,
                    )
                    break
                down_budget += _apply_and_count_step(
                    dto,
                    lambda s=off_state: nsm.raise_state_to_target_cpo(dto, s),
                )
                break

            if hard_status != HARD_STATUS_WHITE_LIST:
                off_state = pick_off_ladder_state(dto)
                if off_state is not None:
                    down_budget += _apply_and_count_step(
                        dto,
                        lambda s=off_state: nsm.raise_state_to_target_cpo(dto, s),
                    )
                else:
                    down_budget += _apply_and_count_step(dto, lambda: nsm.force_off(dto))
                break

            step = resolve_next_effective_step_down(dto.current_mode, catalog)
            log_skipped_aliases(dto.calculated_keyword.text, step.skipped_aliases)
            nxt = step.next_mode
            if nxt is None:
                logger.warning(
                    "v3 shelf_rec_false_cleanup: whitelist ks_id=%s mode=%s, "
                    "step_down returned None; skip",
                    ks_id,
                    dto.current_mode.name,
                )
                break

            if nxt == KeywordStrategyMode.OFF:
                target_state = pick_off_ladder_state(dto)
            else:
                mc = candidate_for_strategy_mode(nxt, catalog)
                place = target_place_from_mode_candidate(mc)
                target_state = ladder_state_for_mode_and_place(dto, nxt, place)
            if target_state is None:
                logger.warning(
                    "v3 shelf_rec_false_cleanup: whitelist ks_id=%s "
                    "target state missing for %s",
                    ks_id,
                    nxt.name,
                )
                break
            down_budget += _apply_and_count_step(
                dto,
                lambda s=target_state: nsm.raise_state_to_target_cpo(dto, s),
            )

        if iterations >= _MAX_SHELF_CLEANUP_ITERATIONS_PER_KEY:
            logger.warning(
                "v3 shelf_rec_false_cleanup: ks_id=%s hit iteration cap",
                dto.keyword_setting_id,
            )

    return down_budget
