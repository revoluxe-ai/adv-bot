"""Executors preamble NORMAL для ``UpdatePipeline``."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.base import (
    UpdateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation import (
    RebalanceExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.hard_status_validate import (
    HardStatusValidateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.max_cpa_guard import (
    MaxCpaGuardExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.not_full_validate import (
    NotFullValidateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.passing_up import (
    PassingUpExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable import (
    PayForOrderGapEnableExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.raise_state_to_target_cpo import (
    RaiseStateToTargetCpoExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.reset_over_max_cpo_on_overspend import (
    ResetOverMaxCpoOnOverspendExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.skip_up_target_place import (
    SkipUpTargetPlaceExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration import (
    ResolveCalibrationExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.shelf_cleanup import (
    ShelfCleanupExecutor,
)


def build_normal_preamble_executors() -> list[UpdateExecutor]:
    """Стандартный порядок NORMAL preamble: V → NF → skip_up → raise → reset → S → R → enable → cal."""
    return [
        HardStatusValidateExecutor(),
        NotFullValidateExecutor(),
        SkipUpTargetPlaceExecutor(),
        RaiseStateToTargetCpoExecutor(),
        ResetOverMaxCpoOnOverspendExecutor(),
        ShelfCleanupExecutor(),
        RebalanceExecutor(),
        PayForOrderGapEnableExecutor(),
        ResolveCalibrationExecutor(),
    ]


__all__ = [
    "RebalanceExecutor",
    "HardStatusValidateExecutor",
    "MaxCpaGuardExecutor",
    "NotFullValidateExecutor",
    "PassingUpExecutor",
    "PayForOrderGapEnableExecutor",
    "RaiseStateToTargetCpoExecutor",
    "ResetOverMaxCpoOnOverspendExecutor",
    "ResolveCalibrationExecutor",
    "ShelfCleanupExecutor",
    "SkipUpTargetPlaceExecutor",
    "UpdateExecutor",
    "build_normal_preamble_executors",
]
