"""Внешние входные данные для сборки ``UpdateContext`` на тик V3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

if TYPE_CHECKING:
    from app.modules.predict_keywords_target_place.clickhouse_manager.dto import (
        BidPosition,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
        CalibrationDirect,
    )


@dataclass
class UpdateContextInput:
    """Базовые данные тика V3 снаружи updater: ключи, plan/fact, профили и gates preamble."""

    keywords: list[CalculatedKeyword]
    plan: PlanData
    fact: FactData
    raw_profiles: dict[str, list[BidPosition]]
    campaign_orders_per_cart_7d: float | None = None
    rec_orders_per_view: float | None = None
    shelf_active: bool = False
    shelf_click_mode: ShelfClickMode = ShelfClickMode.ORGANIC_DOMINANT
    aggressiveness: V3RolloutAggressiveness = V3RolloutAggressiveness.MAX
    plan_fact_equal: bool = True
    views_equal: bool = True
    calibration_direct: CalibrationDirect | None = None
    max_effective_steps: int = 1
    configured_keyword_calibration_max_step: int = 1
    calibration_phase_extra: dict[str, Any] = field(
        default_factory=lambda: dict[str, Any]()
    )
