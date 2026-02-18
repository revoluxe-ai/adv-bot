import asyncio
import logging

from app.common_coroutine.corounines_manager.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class CommonCoroutineManager:

    def __init__(self, workers: list[BaseWorker]):
        self._workers = workers


    async def run(self):
        logger.debug(f"Gathering {len(self._workers)} worker(s)")
        await asyncio.gather(*[worker.run() for worker in self._workers])






