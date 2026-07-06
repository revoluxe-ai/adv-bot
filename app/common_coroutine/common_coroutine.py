"""Entry point for the common coroutine runtime."""

import asyncio
import logging

import dotenv

from app.common_coroutine.corounines_manager import CommonCoroutineManager
from app.common_coroutine.di import CommonCoroutineContainer
from python_modules.logger import setup_logging

dotenv.load_dotenv()

logger = logging.getLogger(__name__)


async def run_runtime() -> None:
    logger.debug("Starting common coroutine runtime")
    container = CommonCoroutineContainer()
    coroutine_manager: CommonCoroutineManager = container.coroutine_manager()
    queue_managers = container.task_queue_managers()
    stop_event = asyncio.Event()

    logger.debug(f"Initializing {len(queue_managers)} task queue(s)")
    queue_tasks = [
        asyncio.create_task(
            queue_manager.run_queue(stop_event),
            name=f"task-queue-{index}",
        )
        for index, queue_manager in enumerate(queue_managers)
    ]

    try:
        logger.debug("Running coroutine manager")
        await coroutine_manager.run()
    finally:
        logger.debug("Shutting down common coroutine runtime")
        stop_event.set()
        if queue_tasks:
            logger.debug(f"Waiting for {len(queue_tasks)} queue task(s) to finish")
            await asyncio.gather(*queue_tasks, return_exceptions=True)
        logger.debug("Runtime shutdown complete")


def run() -> None:
    setup_logging()
    asyncio.run(run_runtime())









