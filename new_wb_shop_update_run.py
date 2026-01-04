"""
Новая точка входа для обработки магазинов

"""

import asyncio
import logging
import platform

import dotenv

from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.modules.shop_runner import run_process_func
from app.modules.shop_runner.exceptions import ShopRunnerCriticalError
from app.utils.redis_cache import setup_redis_cache
from python_modules.logger import setup_logging

dotenv.load_dotenv()
setup_logging()
setup_redis_cache()

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
        async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
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
    # TODO(k8s): При ошибке в этом раннере pod не рестартует. Проверить стратегию перезапуска/пробки
    # и убедиться, что процесс завершается ненулевым кодом при исключениях (иначе Kubernetes не перезапустит).
    asyncio.run(run_process())
