"""
Новая точка входа для обработки магазинов

"""

import asyncio
import platform

import dotenv

from app.modules.shop_runner.exceptions import ShopRunnerCriticalError

dotenv.load_dotenv()
from app.modules.shop_runner import run_process_func
from python_modules.logger import setup_logging

setup_logging()
import logging

system = platform.system()
if system == "Linux":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        asyncio.run(run_process_func.run())
    except Exception as exc:
        raise ShopRunnerCriticalError from exc


# TODO: Проверять активность кампаний перед обновлением ставок
