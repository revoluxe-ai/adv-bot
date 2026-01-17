import logging
import time
from collections.abc import Awaitable, Callable

from app.modules.shop_runner.service_manager.services.plan_fact_controller.dto.plan_fact_stat_dto import PlanFactStatDTO
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_controller import (
    PlanFactController,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.clickhouse_plan_fact_manager import (
    ClickHousePlanFactManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import run_tasks

logger = logging.getLogger(__name__)


class PlanFactManager:
    """Менеджер для обработки план-факта данных всех кампаний и записи в ClickHouse"""

    def __init__(self):
        self._controller = PlanFactController()
        self._clickhouse_manager = ClickHousePlanFactManager()

    async def process_and_save(self, advs: list[ComplexAdv]) -> None:
        """
        Обрабатывает все кампании и записывает данные в ClickHouse.

        Args:
            advs: Список кампаний для обработки
        """
        if not advs:
            return None

        version = time.time()

        handlers: list[Callable[[], Awaitable[PlanFactStatDTO | None]]] = [
            lambda adv=adv: self._controller.process_adv(adv, version) for adv in advs
        ]

        results: list[PlanFactStatDTO | None | BaseException] = await run_tasks(
            handlers,
            max_workers=max(1, min(len(handlers), 16)),
            return_exceptions=True,
        )

        # Собираем успешные результаты
        plan_fact_stats: list[PlanFactStatDTO] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.error(
                    "Ошибка обработки план-факта для adv_id=%s: %s",
                    advs[i].adv_id,
                    result,
                )
            elif result is not None:
                plan_fact_stats.append(result)

        # Записываем в ClickHouse батчем
        if plan_fact_stats:
            await self._clickhouse_manager.insert_plan_fact_stats(plan_fact_stats)
        return None

