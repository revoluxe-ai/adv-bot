"""Executors preamble NORMAL для ``UpdatePipeline``.

Порядок: V → NF → skip_up → raise → reset → S → R → enable → pfo_off → cal.

**Нет отдельной фазы ``cap_down`` (legacy ``CapDownExecutor`` / ``plan_mode_cap_down``):**

- нет CH-профиля (PFO или GAP) → **NF** (`NotFullValidateExecutor`): active → MIN;
  ``target_place`` — migrate + plan-fact (`NotFullTargetPlace*Executor``);
- есть CH-профиля → лестница и CPO из профиля (FULL); отдельный cap по ``max_allowed_mode`` не нужен.

См. ``docks/V3_UPDATER_VALIDATION.md`` § «Cap-down (legacy B) — намеренно удалён».
"""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.base import (
    PreambleExecutor,
    UpdateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation import (
    RebalanceExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.hard_status_validate import (
    HardStatusValidateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.not_full_target_place import (
    NotFullTargetPlaceMigrateExecutor,
    NotFullTargetPlaceOverspendResetExecutor,
    NotFullTargetPlacePlanFactExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.not_full_validate import (
    NotFullValidateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable import (
    PayForOrderGapEnableExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_over_max_off_on_deep_overspend import (
    PayForOrderOverMaxOffOnDeepOverspendExecutor,
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


def build_normal_preamble_executors() -> list[PreambleExecutor]:
    """Стандартный порядок NORMAL preamble (без legacy ``cap_down`` — см. module docstring)."""
    return [
        HardStatusValidateExecutor(),
        NotFullValidateExecutor(),
        NotFullTargetPlaceMigrateExecutor(),
        NotFullTargetPlaceOverspendResetExecutor(),
        NotFullTargetPlacePlanFactExecutor(),
        SkipUpTargetPlaceExecutor(),
        RaiseStateToTargetCpoExecutor(),
        ResetOverMaxCpoOnOverspendExecutor(),
        ShelfCleanupExecutor(),
        RebalanceExecutor(),
        PayForOrderGapEnableExecutor(),
        PayForOrderOverMaxOffOnDeepOverspendExecutor(),
        ResolveCalibrationExecutor(),
    ]


__all__ = [
    "RebalanceExecutor",
    "HardStatusValidateExecutor",
    "NotFullTargetPlaceMigrateExecutor",
    "NotFullTargetPlaceOverspendResetExecutor",
    "NotFullTargetPlacePlanFactExecutor",
    "NotFullValidateExecutor",
    "PayForOrderGapEnableExecutor",
    "PayForOrderOverMaxOffOnDeepOverspendExecutor",
    "PreambleExecutor",
    "RaiseStateToTargetCpoExecutor",
    "ResetOverMaxCpoOnOverspendExecutor",
    "ResolveCalibrationExecutor",
    "ShelfCleanupExecutor",
    "SkipUpTargetPlaceExecutor",
    "UpdateExecutor",
    "build_normal_preamble_executors",
]
