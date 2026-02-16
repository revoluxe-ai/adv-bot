from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from ..while_decorator import while_coroutine_decorator
from .clickhouse_manager import ClickhouseManager
import logging

from ...corounines_manager.base_worker import BaseWorker

logger = logging.getLogger(__name__)



class FillKeywordDeltas(BaseWorker):

    def __init__(self,
                 tasks_queue_manager: TasksManager,
                 clickhouse_manager: ClickhouseManager,
                 from_time_hours: int,
                 update_period_time_minutes: int):
        self._tasks_queue_manager = tasks_queue_manager
        self._clickhouse_manager = clickhouse_manager
        self._from_time_hours = from_time_hours
        self._update_period_time_sec = update_period_time_minutes * 60


    async def run(self):
        await while_coroutine_decorator(self._update_period_time_sec, 60)(self._update)()

    async def _update(self):
        logger.debug(f"Adding task to fill keyword deltas (from_time_hours={self._from_time_hours})")
        future = await self._tasks_queue_manager.add_task(
            lambda : self._clickhouse_manager.fill_keyword_deltas(self._from_time_hours)
        )
        result = await future
        logger.debug(f"Task completed for from_time_hours={self._from_time_hours}: {result}")





