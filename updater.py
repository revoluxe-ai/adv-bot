import dotenv

dotenv.load_dotenv()

from app.modules.wb_adv_updater.runner import (
    run_main_coroutines,
    run_update_all_keywords_on_wb,
)
from python_modules.logger import setup_logging
import logging
import asyncio
from multiprocessing import Process
from functools import partial
import time
import psutil


logger = logging.getLogger(__name__)


async def update_keywords_ctr_by_similary_run():
    from app.modules.wb_adv_updater import (
        hard_ml_data_updater_process as hard_data_manager,
    )

    while True:
        try:
            await hard_data_manager.update_keywords_ctr_by_similary()
        except:
            logger.error("Ошибка обновления по похожему CTR процессов", exc_info=True)
        await asyncio.sleep(60)


run_own_process_list = [
    update_keywords_ctr_by_similary_run,
    run_update_all_keywords_on_wb,
    run_main_coroutines,
]


def process_controller(process_pids: list[int], process_names: list[str]):
    time.sleep(10)
    while True:
        for pid, name in zip(process_pids, process_names):
            logger.debug(f"Проверка процесса: {name}")
            try:
                proc = psutil.Process(pid)
                assert proc.is_running()
            except psutil.NoSuchProcess:
                logger.error(f"Процесс с PID {pid} (имя: {name}) не существует.")
                continue
        time.sleep(60)


def run_coroutines(coroutine):
    asyncio.run(coroutine())


def main() -> None:
    processes = []
    process_pids = []
    process_names = []

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
            logging.error("Произошла ошибка:", exc_info=True)
            del e
            continue  # Продолжение работы программы после других исключений
