"""Планировщик сценариев управления кампаниями."""

import logging

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.cascade import (
    ControlCascade,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.data_classes import (
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.executors.exponent_executor import (
    ExponentDownExecutor,
    ExponentRaiseExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.executors.target_place_executor import (
    TargetPlaceDownExecutor,
    TargetPlaceUpExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.executors.white_list_executor import (
    WhiteListAddExecutor,
    WhiteListRemoveExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.sales_state.sales_states import (
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
    """

    def __init__(self):
        """Инициализирует сценарии для каждого состояния."""
        self.scenarios = {
            SalesStates.OVERSPEND: [
                WhiteListRemoveExecutor(),
                ExponentRaiseExecutor(),
                TargetPlaceDownExecutor(),
            ],
            SalesStates.UNDERPERFORM: [
                TargetPlaceUpExecutor(),
                WhiteListAddExecutor(),
                ExponentDownExecutor(),
            ],
            SalesStates.STABLE: [
                TargetPlaceDownExecutor(),
                WhiteListRemoveExecutor(),
                ExponentRaiseExecutor(),
            ],
            SalesStates.OPTIMAL: [],
        }

    async def run_for_state(self, ctx: PipelineContext) -> None:
        """Запускает сценарий для текущего состояния кампании.
        
        Args:
            ctx: Контекст выполнения с состоянием кампании
        """
        executors = self.scenarios.get(ctx.state, [])

        if not executors:
            logger.info(
                f"[adv_id={ctx.adv.adv_id}] Состояние {ctx.state.name}: "
                "действий не требуется"
            )
            return

        cascade = ControlCascade(executors)
        await cascade.run(ctx)

