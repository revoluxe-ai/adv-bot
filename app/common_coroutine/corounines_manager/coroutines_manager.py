import asyncio
import logging

from app.common_coroutine.corounines_manager.base_worker import BaseWorker

logger = logging.getLogger(__name__)

WORKER_RESTART_DELAY_SECONDS = 5


class CommonCoroutineManager:

    def __init__(self, workers: list[BaseWorker]):
        self._workers = workers

    async def _run_worker_forever(self, worker: BaseWorker) -> None:
        worker_name = worker.__class__.__name__
        restart_count = 0
        while True:
            try:
                await worker.run()
                logger.warning(
                    "Worker %s stopped unexpectedly, restarting in %ss",
                    worker_name,
                    WORKER_RESTART_DELAY_SECONDS,
                    extra={
                        "component": "common_coroutine_worker",
                        "worker": worker_name,
                        "restart_count": restart_count,
                        "retry_in_sec": WORKER_RESTART_DELAY_SECONDS,
                    },
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                restart_count += 1
                logger.error(
                    "Worker %s crashed, restarting",
                    worker_name,
                    exc_info=True,
                    extra={
                        "component": "common_coroutine_worker",
                        "worker": worker_name,
                        "restart_count": restart_count,
                        "retry_in_sec": WORKER_RESTART_DELAY_SECONDS,
                    },
                )
            await asyncio.sleep(WORKER_RESTART_DELAY_SECONDS)

    async def run(self):
        logger.debug(f"Gathering {len(self._workers)} worker(s)")
        await asyncio.gather(
            *[self._run_worker_forever(worker) for worker in self._workers]
        )






