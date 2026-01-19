"""Воркер для обновления магазинов."""

import asyncio

import dotenv
from aiohttp import ClientSession

from app.core.di.di_manager import DIManager
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.shop_run_worker.redis_manager.redis_manager import (
    RedisShopManager,
)
from app.modules.shop_runner.shop_run_worker.worker.worker import ShopWorker
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.settings import settings
from app.utils.redis_cache import setup_redis_cache
from python_modules.logger import setup_logging

# TODO: Сделать единую функцию загрузчик этого всего для всех точек входа?
dotenv.load_dotenv()
setup_logging()
setup_redis_cache()

async def run_shop_update_worker() -> None:
    """Запускает воркер для обновления магазинов."""
    from app.core.di.app_container import AppContainer

    tasks_manager = TasksManager(max_workers=settings.MAX_TASKS)
    plan_fact_reader = PlanFactReader()
    redis_manager = RedisShopManager()
    stop_event = asyncio.Event()
    queue_task = asyncio.create_task(tasks_manager.run_queue(stop_event))
    try:
        async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
            async with ClientSession() as session:
                worker = ShopWorker(
                    session,
                    tasks_manager=tasks_manager,
                    plan_fact_reader=plan_fact_reader,
                    redis_manager=redis_manager,
                )
                await worker.update_active_shop_update_tasks_run()
    finally:
        stop_event.set()
        await queue_task


if __name__ == "__main__":
    asyncio.run(run_shop_update_worker())
