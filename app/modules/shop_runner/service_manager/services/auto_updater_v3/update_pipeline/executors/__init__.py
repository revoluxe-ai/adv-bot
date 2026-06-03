"""Executors preamble NORMAL для ``UpdatePipeline``."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.base import (
    UpdateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cap_down import (
    CapDownExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation import (
    CostReallocationExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.hard_status_validate import (
    HardStatusValidateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.max_cpa_guard import (
    MaxCpaGuardExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.passing_up import (
    PassingUpExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable import (
    PayForOrderGapEnableExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration import (
    ResolveCalibrationExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.shelf_cleanup import (
    ShelfCleanupExecutor,
)


def build_normal_preamble_executors() -> list[UpdateExecutor]:
    """Стандартный порядок NORMAL preamble: V → B → U → S → G → R → enable → calibration."""
    return [
        HardStatusValidateExecutor(),
        CapDownExecutor(),
        PassingUpExecutor(),
        ShelfCleanupExecutor(),
        MaxCpaGuardExecutor(),
        CostReallocationExecutor(),
        PayForOrderGapEnableExecutor(),
        ResolveCalibrationExecutor(),
    ]


__all__ = [
    "CapDownExecutor",
    "CostReallocationExecutor",
    "HardStatusValidateExecutor",
    "MaxCpaGuardExecutor",
    "PassingUpExecutor",
    "PayForOrderGapEnableExecutor",
    "ResolveCalibrationExecutor",
    "ShelfCleanupExecutor",
    "UpdateExecutor",
    "build_normal_preamble_executors",
]
