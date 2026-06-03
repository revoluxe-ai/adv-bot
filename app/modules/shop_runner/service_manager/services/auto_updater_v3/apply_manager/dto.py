"""DTO входа/выхода ``ApplyManager``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.dto import (
    TickData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
        UpdateContext,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.runner import (
        PreamblePipelineRunResult,
    )


@dataclass
class V3ApplyInput:
    """Итог тика перед персистом: post-gate, flush, Redis, target_place."""

    tick_data: TickData
    update_context: UpdateContext | None
    pipeline_result: PreamblePipelineRunResult | None
    calibration_executed: bool
    sync_force_zero: bool


@dataclass
class V3ApplyResult:
    """Результат ``ApplyManager.apply``."""

    post_gate_actions: list[V3Action]
    flushed_to_db: bool
    target_place_synced: bool
    plan_fact_cached: bool
    views_cached: bool
    calibration_cached: bool
