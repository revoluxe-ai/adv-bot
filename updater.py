import asyncio
import logging
import time
from functools import partial
from multiprocessing import Process

import dotenv
import psutil
from typing import NoReturn
from app.modules.wb_adv_updater.runner import (
    run_main_coroutines,
    run_update_all_keywords_on_wb,
)
from python_modules.logger import setup_logging

dotenv.load_dotenv()

logger = logging.getLogger(__name__)


async def update_keywords_ctr_by_similary_run() -> NoReturn:
    from app.modules.wb_adv_updater import (
        hard_ml_data_updater_process as hard_data_manager,
    )

    while True:
        try:
            await hard_data_manager.update_keywords_ctr_by_similary()
        except Exception:
            logger.error("Ошибка обновления по похожему CTR процессов", exc_info=True)
        await asyncio.sleep(60)


# Явная аннотация типов для списка корутин
run_own_process_list: list[Callable[..., Never]] = [
    update_keywords_ctr_by_similary_run,
    run_update_all_keywords_on_wb,
    run_main_coroutines,
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

def run_coroutines(coroutine_func: Callable[..., Coroutine[Any, Any, Never]]) -> None:
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
    level = logging.INFO
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
