import asyncio
import logging

from app.common_coroutine.corounines_manager.base_worker import BaseWorker
from app.utils.backoff import exponential_retry_delay_seconds

logger = logging.getLogger(__name__)

WORKER_RESTART_BASE_DELAY_SECONDS = 5
WORKER_RESTART_MAX_DELAY_SECONDS = 300
WORKER_RESTART_RESET_AFTER_UPTIME_SECONDS = WORKER_RESTART_MAX_DELAY_SECONDS


class CommonCoroutineManager:

    def __init__(self, workers: list[BaseWorker]):
        self._workers = workers

    async def _run_worker_forever(self, worker: BaseWorker) -> None:
        worker_name = worker.__class__.__name__
        restart_count = 0
        while True:
            run_started_at = asyncio.get_running_loop().time()
            try:
                await worker.run()
            except asyncio.CancelledError:
                raise
            except Exception:
                uptime_seconds = asyncio.get_running_loop().time() - run_started_at
                # If worker stayed healthy long enough, consider this crash isolated
                # and restart backoff from the initial step.
                if uptime_seconds >= WORKER_RESTART_RESET_AFTER_UPTIME_SECONDS:
                    restart_count = 0
                restart_count += 1
                retry_in_sec = exponential_retry_delay_seconds(
                    restart_count,
                    base_seconds=WORKER_RESTART_BASE_DELAY_SECONDS,
                    max_seconds=WORKER_RESTART_MAX_DELAY_SECONDS,
                )
                logger.error(
                    "Worker %s crashed, restarting in %ss",
                    worker_name,
                    retry_in_sec,
                    exc_info=True,
                    extra={
                        "component": "common_coroutine_worker",
                        "worker": worker_name,
                        "uptime_seconds": round(uptime_seconds, 3),
                        "restart_count": restart_count,
                        "retry_in_sec": retry_in_sec,
                    },
                )
            else:
                # A clean stop means crash streak is broken. Restart with base delay,
                # but keep counter reset so a future crash starts from attempt #1 too.
                restart_count = 0
                retry_in_sec = exponential_retry_delay_seconds(
                    1,
                    base_seconds=WORKER_RESTART_BASE_DELAY_SECONDS,
                    max_seconds=WORKER_RESTART_MAX_DELAY_SECONDS,
                )
                logger.warning(
                    "Worker %s stopped unexpectedly, restarting in %ss",
                    worker_name,
                    retry_in_sec,
                    extra={
                        "component": "common_coroutine_worker",
                        "worker": worker_name,
                        "restart_count": restart_count,
                        "retry_in_sec": retry_in_sec,
                    },
                )
            await asyncio.sleep(retry_in_sec)

    async def run(self):
        logger.debug(f"Gathering {len(self._workers)} worker(s)")
        _ = await asyncio.gather(
            *(self._run_worker_forever(worker) for worker in self._workers)
        )






