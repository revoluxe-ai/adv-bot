import asyncio
import logging
import time
from functools import partial
from multiprocessing import Process

import dotenv
from typing import Any
from collections.abc import Callable, Coroutine

from app.common_coroutine.common_coroutine import run_runtime
from app.modules.wb_adv_updater.runner import (
    run_main_coroutines,
    # run_update_all_keywords_on_wb, # dead code
)
from app.utils.redis_cache import setup_redis_cache
from python_modules.logger import setup_logging

# SNAPSHOT_* читаются из .env — dotenv до импорта snapshot_data_updater
_ = dotenv.load_dotenv()
setup_redis_cache()

from app.snapshot_data_updater import snapshot_data_updater
from app.snapshot_data_updater.config import reload_snapshot_config

reload_snapshot_config()


logger = logging.getLogger(__name__)

AsyncEntry = Callable[[], Coroutine[Any, Any, None]]


# Явная аннотация типов для списка корутин
run_own_process_list: list[AsyncEntry] = [
    # #  TODO: Закомментировал эти корутины и отправил в прод, что привлело к ошибке
    run_main_coroutines, # здесь вроде только payment корутина
    # # # TODO: привести все процессы к единому интерфейсу
    run_runtime, # тут вроде запуск воркеров, очереди
    snapshot_data_updater.run, # здесь кеш сделать для всего
]


# Обновлена типизация: принимаем обычную async-функцию без аргументов
# (а не DI-провайдер)


def run_coroutines(coroutine_func:  AsyncEntry) -> None:
    asyncio.run(coroutine_func())


def main() -> None:
    process_registry: dict[int, Process] = {}
    restart_count: dict[int, int] = {i: 0 for i, _entry in enumerate(run_own_process_list)}

    def _process_label(index: int, run_own_process: AsyncEntry) -> str:
        return f"{run_own_process.__name__}#{index}"

    def _start_process(index: int, run_own_process: AsyncEntry) -> Process:
        func = partial(run_coroutines, run_own_process)
        process = Process(target=func, name=_process_label(index, run_own_process))
        process.start()
        logger.info(
            "Запущен процесс %s - %s",
            process.pid,
            _process_label(index, run_own_process),
        )
        return process

    for index, run_own_process in enumerate(run_own_process_list):
        process_registry[index] = _start_process(index, run_own_process)

    while True:
        for index, process in list(process_registry.items()):
            if process.is_alive():
                continue

            exit_code = process.exitcode
            run_own_process = run_own_process_list[index]
            restart_count[index] += 1
            process_name = _process_label(index, run_own_process)
            logger.error(
                "Процесс %s завершился (exit_code=%s), перезапуск #%s",
                process_name,
                exit_code,
                restart_count[index],
            )
            process_registry[index] = _start_process(index, run_own_process)

        time.sleep(2)
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
