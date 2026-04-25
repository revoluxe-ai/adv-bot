import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

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
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.pre_complex_adv import (
    PreComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import run_tasks

TItem = TypeVar("TItem")


class PlanFactManager:
    """Менеджер для обработки план-факта данных всех кампаний и записи в ClickHouse"""

    def __init__(self):
        self._controller = PlanFactController()
        self._clickhouse_manager = ClickHousePlanFactManager()

    async def _process_and_save_items(
        self,
        items: list[TItem],
        *,
        processor: Callable[[TItem, float], Awaitable[PlanFactStatDTO | None]],
    ) -> None:
        if not items:
            return None

        version = time.time()
        handlers: list[Callable[[], Awaitable[PlanFactStatDTO | None]]] = [
            lambda item_=item: processor(item_, version) for item in items
        ]

        results: list[PlanFactStatDTO | None] = await run_tasks(
            handlers,
            max_workers=max(1, min(len(handlers), 16)),
            return_exceptions=False,
        )

        plan_fact_stats: list[PlanFactStatDTO] = [
            r for r in results if r is not None
        ]

        if plan_fact_stats:
            await self._clickhouse_manager.insert_plan_fact_stats(plan_fact_stats)
        return None

    async def process_and_save(self, advs: list[ComplexAdv]) -> None:
        """
        Обрабатывает все кампании и записывает данные в ClickHouse.

        Args:
            advs: Список кампаний для обработки
        """
        return await self._process_and_save_items(
            advs,
            processor=self._controller.process_adv,
        )

    async def process_and_save_pre_complex_advs(
        self, pre_advs: list[PreComplexAdv]
    ) -> None:
        """Обрабатывает seed DTO кампаний и записывает план-факт в ClickHouse."""
        return await self._process_and_save_items(
            pre_advs,
            processor=self._controller.process_pre_adv,
        )

