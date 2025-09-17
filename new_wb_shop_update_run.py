"""Новая точка входа для обработки магазинов"""

import asyncio
import logging
import platform

import dotenv

from app.modules.shop_runner.exceptions import ShopRunnerCriticalError

dotenv.load_dotenv()
from app.core.di import AppContainer
from app.modules.shop_runner import run_process_func
from python_modules.logger import setup_logging

dotenv.load_dotenv()
setup_logging()

system = platform.system()
if system == "Linux":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


logger = logging.getLogger(__name__)

container = AppContainer()


async def run_process() -> None:
    """Запуск общего процесса на все магазины, legacy, нуждается в рефакторинге.

    TODO: Выпилить магазинные функции из общего процесса и перенести их в shop_runner. Тут оставить только общие.
    """
    try:
        result = container.init_resources()
        if result is None:
            await run_process_func.run()
    except ShopRunnerCriticalError as exc:
        logger.critical(f"Критическая ошибка в процессе: {exc}", exc_info=True)
        raise exc

    finally:
        result = container.shutdown_resources()
        if result is not None:
            await result


if __name__ == "__main__":
    # TODO: Проверять активность кампаний перед обновлением ставок
    asyncio.run(run_process())
