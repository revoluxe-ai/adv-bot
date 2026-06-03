"""Фаза S: shelf rec-false cleanup down."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.base import (
    UpdateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    plan_shelf_rec_false_cleanup_down,
)


class ShelfCleanupExecutor(UpdateExecutor):
    """SHELF_REC_CLEANUP."""

    phase_name = "shelf_cleanup"

    def check_skip(self, context: UpdateContext) -> str | None:
        if not context.adv_state.shelf_active:
            return "shelf_inactive"
        return None

    def plan_actions(self, context: UpdateContext) -> list[V3Action]:
        state = context.adv_state
        return plan_shelf_rec_false_cleanup_down(
            context.prepared,
            click_mode=state.shelf_click_mode,
            ladder_inputs=state.ladder_inputs,
            policy=state.policy,
        )
