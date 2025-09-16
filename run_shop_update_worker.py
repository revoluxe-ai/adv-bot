import dotenv

dotenv.load_dotenv()
import asyncio

from aiohttp import ClientSession

from app.modules.shop_runner.shop_run_worker.worker.worker import ShopWorker
from python_modules.logger import setup_logging

setup_logging()


async def run_shop_update_worker() -> None:
    async with ClientSession() as session:
        worker = ShopWorker(session)
        await worker.update_active_shop_update_tasks_run()


if __name__ == "__main__":
    asyncio.run(run_shop_update_worker())
