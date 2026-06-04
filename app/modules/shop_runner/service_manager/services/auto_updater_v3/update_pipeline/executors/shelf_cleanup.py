"""Фаза S: shelf rec-false cleanup down (in-place через ``NextStateManager``)."""

from __future__ import annotations

import logging

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    log_skipped_aliases,
    resolve_next_effective_step_down,
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    HARD_STATUS_AUTO_MODE,
    HARD_STATUS_WHITE_LIST,
    is_v3_operable_hard_status,
)

logger = logging.getLogger(__name__)


class ShelfCleanupExecutor:
    """SHELF_REC_CLEANUP: effective DOWN / FORCE_OFF по rec-gate FAIL на текущем state."""

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
        _run_shelf_rec_cleanup(
            context,
            click_mode=state.shelf_click_mode,
            ladder_inputs=state.ladder_inputs,
            policy=state.policy,
            nsm=self._next_state_manager,
        )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _run_shelf_rec_cleanup(
    context: UpdateContext,
    *,
    click_mode: ShelfClickMode,
    ladder_inputs,
    policy: SelectionPolicy | None,
    nsm: NextStateManager,
) -> None:
    """Cleanup активных ключей с ``RecGateStatus.FAIL`` на текущем state."""
    if not shelf_rec_conversion_policy_active(click_mode):
        return

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
        return

    dto_by_ks: dict[int, KeywordDTO] = {
        dto.keyword_setting_id: dto for dto in context.keywords
    }

    for ctx, mode in prepared:
        if mode == KeywordStrategyMode.OFF:
            continue
        hard_status = int(ctx.keyword.hard_status)
        if not is_v3_operable_hard_status(hard_status):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        dto = dto_by_ks.get(int(ks_id))
        if dto is None:
            continue

        state_candidates = mode_catalog_for_ctx(ctx, prepared, ladder_inputs=ladder)
        opc = ladder.orders_per_cart_for_ctx(ctx)
        current_status = state_rec_gate_status_for_mode(
            state_candidates,
            mode,
            gate_policy,
            rec_orders_per_view=rec,
            orders_per_cart=opc,
        )
        if not rec_gate_triggers_cleanup(current_status):
            continue

        min_status = state_rec_gate_status_for_mode(
            state_candidates,
            KeywordStrategyMode.MIN_CPA,
            gate_policy,
            rec_orders_per_view=rec,
            orders_per_cart=opc,
        )

        if rec_gate_allows_up(min_status) and mode != KeywordStrategyMode.MIN_CPA:
            if hard_status == HARD_STATUS_WHITE_LIST:
                nsm.set_keyword_strategy_mode(dto, KeywordStrategyMode.MIN_CPA)
            else:
                nsm.force_off(dto)
            continue

        if hard_status == HARD_STATUS_WHITE_LIST:
            step = resolve_next_effective_step_down(mode, state_candidates)
            log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
            nxt = step.next_mode
            if nxt is None:
                if mode == KeywordStrategyMode.MIN_CPA:
                    logger.warning(
                        "v3 shelf_rec_false_cleanup: whitelist ks_id=%s at MIN, "
                        "step_down returned None; fallback OFF",
                        ks_id,
                    )
                    nxt = KeywordStrategyMode.OFF
                else:
                    logger.warning(
                        "v3 shelf_rec_false_cleanup: whitelist ks_id=%s mode=%s, "
                        "step_down returned None; skip cleanup",
                        ks_id,
                        mode.name,
                    )
                    continue
            nsm.set_keyword_strategy_mode(dto, nxt)
        else:
            nsm.force_off(dto)
