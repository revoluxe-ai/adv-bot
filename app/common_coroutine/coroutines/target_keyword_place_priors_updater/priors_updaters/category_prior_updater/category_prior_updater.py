import logging

from app.common_coroutine.corounines_manager.base_worker import BaseWorker
from app.common_coroutine.coroutines.while_decorator import while_coroutine_decorator
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from .clickhouse_manager import ClickHouseManager

logger = logging.getLogger(__name__)


class CategoryPriorUpdater(BaseWorker):
    def __init__(self,
                 tasks_manager: TasksManager,
                 click_house_manager: ClickHouseManager,
                 update_period_seconds: int):
        self._tasks_manager = tasks_manager
        self._click_house_manager = click_house_manager
        self._update_period_seconds = update_period_seconds

    async def run(self):
        await while_coroutine_decorator(self._update_period_seconds, 60)(
            self._update_category_prior
        )()

    async def _update_category_prior(self):
        future = await self._tasks_manager.add_task(
            lambda: self._click_house_manager.update_category_prior()
        )
        try:
            result = await future
        except Exception:
            logger.exception("Error while updating category priors")
        else:
            logger.debug("Category priors update task result: %s", result)
