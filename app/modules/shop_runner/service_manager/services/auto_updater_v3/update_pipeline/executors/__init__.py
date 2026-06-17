"""Executors preamble NORMAL для ``UpdatePipeline``.

Этот модуль задаёт канонический порядок in-place фаз NORMAL-контента и тем
самым фиксирует продуктовый контракт между ladder-контуром FULL и no-CH
контуром PFO/GAP.

Важная мысль этого порядка: фазы здесь не просто перечислены подряд, а
разделяют разные уровни ответственности.

- сначала идут phase-gates, которые только подготавливают режим;
- затем идёт clamp фаза, которая понижает ключи выше aggression cap;
- затем идут bootstrap-фазы, которые один раз инициализируют target_place;
- затем идут коррекции, которые двигают уже инициализированный target_place;
- отдельно живут ladder-only фазы для FULL;
- отдельно живут GAP enable/reset фазы, потому что у GAP ещё нет права
  участвовать в NF bootstrap.

Порядок фаз:
V → clamp → resolve_clamp → NF → NF_migrate → NF_plan_fact → skip_up → raise →
reset → S → R → enable → pfo_off → cal → resolve_clamp.

Смысл разбиения:
- **NF** (`NotFullValidateExecutor`) переводит активные PFO ключи в
  ``MIN_CPA`` и оставляет ``OFF`` без изменений;
- **NF_migrate** (`NotFullTargetPlaceMigrateExecutor`) инициализирует стартовый
  ``target_place`` текущей WB-позицией только для активных PFO ключей с
  нулевым target_place;
- **NF_plan_fact** (`NotFullTargetPlacePlanFactExecutor`) выполняет только
  ``±1`` по fact/resolve после bootstrap, не затрагивая FULL и не делая reset
  в ``0``;
- **skip_up / raise / reset / shelf / rebalance / calibration** обслуживают
  исключительно FULL ladder-контур;
- финальный ``resolve_clamp`` в конце pipeline гарантирует, что later UP-фазы не
  вернут state выше current resolve, но получает отдельный ``phase_id`` для
  отчётности;

В итоге этот модуль работает как “карта движений” для NORMAL pipeline: он
объясняет, где начинается PFO bootstrap, где заканчивается NF-коррекция и где
начинаются отдельные GAP и FULL ветки.

Отдельной фазы ``cap_down`` (legacy ``CapDownExecutor`` / ``plan_mode_cap_down``)
здесь нет: её контракт полностью заменён явным делением на FULL, PFO и GAP.
Подробности и обоснование — в ``docks/V3_UPDATER_VALIDATION.md``.
"""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.base import (
    PreambleExecutor,
    UpdateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation import (
    RebalanceExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.clamp_state_to_aggression import (
    ClampStateToAggressionExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.clamp_states_to_resolve_when_no_effective_steps import (
    ClampStatesToResolveWhenNoEffectiveStepsExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.hard_status_validate import (
    HardStatusValidateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.not_full_target_place import (
    NotFullTargetPlaceMigrateExecutor,
    NotFullTargetPlacePlanFactExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.not_full_validate import (
    NotFullValidateExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable import (
    PayForOrderGapEnableExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_no_ch_enable import (
    PayForOrderNoChEnableExecutor,
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
        ClampStateToAggressionExecutor(),
        ClampStatesToResolveWhenNoEffectiveStepsExecutor(
            phase_name="clamp_states_to_resolve_when_no_effective_steps",
        ),
        NotFullValidateExecutor(),
        NotFullTargetPlaceMigrateExecutor(),
        NotFullTargetPlacePlanFactExecutor(),
        SkipUpTargetPlaceExecutor(),
        RaiseStateToTargetCpoExecutor(),
        ResetOverMaxCpoOnOverspendExecutor(),
        ShelfCleanupExecutor(),
        PayForOrderNoChEnableExecutor(),
        RebalanceExecutor(),
        PayForOrderGapEnableExecutor(),
        PayForOrderOverMaxOffOnDeepOverspendExecutor(),
        ResolveCalibrationExecutor(),
        ClampStatesToResolveWhenNoEffectiveStepsExecutor(
            phase_name="final_clamp_states_to_resolve",
        ),
    ]


__all__ = [
    "ClampStateToAggressionExecutor",
    "ClampStatesToResolveWhenNoEffectiveStepsExecutor",
    "RebalanceExecutor",
    "HardStatusValidateExecutor",
    "NotFullTargetPlaceMigrateExecutor",
    "NotFullTargetPlacePlanFactExecutor",
    "NotFullValidateExecutor",
    "PayForOrderGapEnableExecutor",
    "PayForOrderNoChEnableExecutor",
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
