"""Планировщик сценариев управления кампаниями."""

import logging

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.cascades.control_cascade import (
    ControlCascade,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    PipelineContext,
)

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.target_place_executor.target_place_down_executor import (
    TargetPlaceDownExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.target_place_executor.target_place_up_executor import (
    TargetPlaceUpExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.white_list_executor.white_list_add_executor import (
    WhiteListAddExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.white_list_executor.white_list_remove_executor import (
    WhiteListRemoveExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)

logger = logging.getLogger(__name__)


class ScenarioPlanner:
    """Формирует последовательность действий по состоянию adv.

    Цепочки исполнителей для каждого состояния:

    - OVERSPEND (снизить расход):
        1. Убрать ключ из БС
        2. → Повысить экспоненту (+1, макс 20)
        3. → Понизить ЦП (+1, мин 300)

    - UNDERPERFORM (нарастить продажи):
        1. Повысить ЦП (-1, макс 1)
        2. → Добавить релевантные ключи
        3. → Понизить экспоненту (-1, мин 1)

    - STABLE (снизить себестоимость):
        1. Понизить ЦП (+1)
        2. → Убрать ключи из БС
        3. → Повысить экспоненту (+1, макс 20)

    - OPTIMAL: ничего не делаем
    - NO_DATA (Н): V3 — MIN_CPA + target_place=0; V2 — без исполнителей
    """

    def __init__(self):
        """Инициализирует сценарии для каждого состояния."""
        self.scenarios = {
            SalesStates.OVERSPEND: [
                WhiteListRemoveExecutor(),
                TargetPlaceDownExecutor(),
            ],
            SalesStates.UNDERPERFORM: [
                TargetPlaceUpExecutor(),
                WhiteListAddExecutor(),
            ],
            SalesStates.STABLE: [
                TargetPlaceDownExecutor(),
                WhiteListRemoveExecutor(),
            ],
            SalesStates.OPTIMAL: [],
            SalesStates.NO_DATA: [],
        }

    async def run_for_state(self, ctx: PipelineContext) -> None:
        """Запускает сценарий для текущего состояния кампании.

        Args:
            ctx: Контекст выполнения с состоянием кампании
        """
        executors = self.scenarios.get(ctx.state, [])

        if not executors:
            logger.info(
                f"[adv_id={ctx.complex_adv.adv_id}] Состояние {ctx.state.name}: "
                "действий не требуется"
            )
            return

        cascade = ControlCascade(executors)
        await cascade.run(ctx)
