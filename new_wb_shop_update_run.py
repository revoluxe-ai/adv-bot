"""
Новая точка входа для обработки магазинов

"""

import asyncio
import platform

import dotenv
import logging

from app.core.di.di_manager import DIManager
from app.modules.shop_runner.exceptions import ShopRunnerCriticalError
from app.modules.shop_runner import run_process_func
from python_modules.logger import setup_logging
from app.core.di import AppContainer

dotenv.load_dotenv()
setup_logging()

system = platform.system()
if system == "Linux":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)


async def run_process() -> None:
    """Запуск общего процесса на все магазины, legacy, нуждается в рефакторинге.

    TODO: Выпилить магазинные функции из общего процесса и перенести их в shop_runner. Тут оставить только общие.
    """
    # TODO: Обновлять список пакетов/модулей в wire(), если появляются новые инъекции (@inject/Provide[...]).
    # Проверка/тест идеи
    # Быстрая проверка на запуск: этого достаточно.
    # Для системной проверки (позже): написать скрипт, который ищет Provide[...]/@inject и сверяет,
    # что соответствующие файлы входят в списки packages/modules переданные в wire().
    # Либо держать единый модуль app/core/di/wiring.py со списком пакетов, и дергать его из всех раннеров.
    # Запуск процесса без явного lifecycle-менеджмента, ресурсы не требуются
    # TODO: При необходимости добавить точечную инициализацию ресурсов (например, Redis)
    try:
        async with await DIManager.create(AppContainer):
            await run_process_func.run()
    except ShopRunnerCriticalError as exc:
        logger.critical(f"Критическая ошибка в процессе: {exc}", exc_info=True)
        raise exc
    except Exception as exc:
        logger.error(f"Ошибка в процессе: {exc}", exc_info=True)
        raise exc
    finally:
        pass


if __name__ == "__main__":
    # TODO: Проверять активность кампаний перед обновлением ставок
    asyncio.run(run_process())
