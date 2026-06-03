"""Фаза B: cap down по tier eligibility."""

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_preamble_phases import (
    plan_mode_cap_down,
)


class CapDownExecutor(UpdateExecutor):
    """MODE_CAP_DOWN (фаза B)."""

    phase_name = "cap_down"

    def plan_actions(self, context: UpdateContext) -> list[V3Action]:
        state = context.adv_state
        return plan_mode_cap_down(
            context.keyword_batch.to_legacy_prepared(),
            eligibility_by_ks_id=state.eligibility_by_ks_id,
        )
