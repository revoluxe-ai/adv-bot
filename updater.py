import asyncio
import logging
import time
from functools import partial
from multiprocessing import Process

import dotenv
import psutil # pyright: ignore
from typing import Any
from collections.abc import Callable, Coroutine

from app.common_coroutine import common_coroutine
# Use direct imports to avoid any re-export typing issues
from app.modules.wb_adv_updater.runner import (
    run_main_coroutines,
    # run_update_all_keywords_on_wb, # dead code
)
from app.utils.redis_cache import setup_redis_cache
from python_modules.logger import setup_logging

dotenv.load_dotenv()
setup_redis_cache()


logger = logging.getLogger(__name__)


AsyncEntry = Callable[[], Coroutine[Any, Any, None]]


# Явная аннотация типов для списка корутин
run_own_process_list: list[AsyncEntry] = [
    #  TODO: Закомментировал эти корутины и отправил в прод, что привлело к ошибке
    run_update_all_keywords_on_wb,
    run_main_coroutines,
    # TODO: привести все процессы к единому интерфейсу
    common_coroutine.run # type: ignore # pyright: ignore
]


def process_controller(process_pids: list[int], process_names: list[str]) -> None:
    time.sleep(10)
    while True:
        for pid, name in zip(process_pids, process_names, strict=False):
            logger.debug(f"Проверка процесса: {name}")
            try:
                proc = psutil.Process(pid)
                assert proc.is_running()
            except psutil.NoSuchProcess:
                logger.error(f"Процесс с PID {pid} (имя: {name}) не существует.")
                continue
        time.sleep(60)


# Обновлена типизация: принимаем обычную async-функцию без аргументов
# (а не DI-провайдер)


def run_coroutines(coroutine_func:  AsyncEntry) -> None:
    asyncio.run(coroutine_func())


def main() -> None:
    processes: list[Process] = []
    process_pids: list[int | None] = []
    process_names: list[str] = []

    for run_own_process in run_own_process_list:
        func = partial(run_coroutines, run_own_process)
        process = Process(target=func, name=run_own_process.__name__)
        process.start()
        logger.info(f"Запущен процесс {process.pid} - {run_own_process.__name__}")
        processes.append(process)
        process_pids.append(process.pid)
        process_names.append(run_own_process.__name__)

    for process in processes:
        process.join()
    return None


if __name__ == "__main__":
    level = logging.DEBUG
    setup_logging()
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("Программа остановлена пользователем.")
            break  # Выход из цикла, завершение программы
        except InterruptedError:
            raise  # Перевыбрасывание исключения
        except Exception as e:
            logging.critical("Произошла ошибка:", exc_info=True)
            raise e
