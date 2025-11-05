"""Воркер для обновления магазинов."""

import asyncio

import dotenv
from aiohttp import ClientSession

from app.core.di.di_manager import DIManager
from app.modules.shop_runner.shop_run_worker.worker.worker import ShopWorker
from python_modules.logger import setup_logging

dotenv.load_dotenv()
setup_logging()


async def run_shop_update_worker() -> None:
    """Запускает воркер для обновления магазинов."""
    from app.core.di.app_container import AppContainer

    async with await DIManager.create(AppContainer): # type: ignore[attr-defined]
        async with ClientSession() as session:
            worker = ShopWorker(session)
            await worker.update_active_shop_update_tasks_run()


if __name__ == "__main__":
    asyncio.run(run_shop_update_worker())
