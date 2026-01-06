"""Воркер для обновления магазинов."""

import asyncio

import dotenv
from aiohttp import ClientSession

from app.core.di.di_manager import DIManager
from app.modules.shop_runner.shop_run_worker.worker.worker import ShopWorker
from app.utils.redis_cache import setup_redis_cache
from python_modules.logger import setup_logging

# TODO: Сделать единую функцию загрузчик этого всего для всех точек входа?
dotenv.load_dotenv()
setup_logging()
setup_redis_cache()

async def run_shop_update_worker() -> None:
    """Запускает воркер для обновления магазинов."""
    from app.core.di.app_container import AppContainer

    async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
        async with ClientSession() as session:
            worker = ShopWorker(session)
            await worker.update_active_shop_update_tasks_run()


if __name__ == "__main__":
    asyncio.run(run_shop_update_worker())
