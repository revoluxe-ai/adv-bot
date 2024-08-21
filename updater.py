from app.modules.wb_adv_updater.bidder import run_bidder_process


from app.modules.wb_adv_updater.runner import (
    run_main_coroutines,
    keywords_parsing_process,
    run_update_vectors_in_redis,
    run_update_minus_keywords_on_wb,
    run_update_keyword_stat,
    update_all_data_in_db,
    parser_all_white_phrase,
    run_update_predict_ctr,
    run_update_model
)
from python_modules.logger import setup_logging
import logging
import asyncio
from multiprocessing import Process
from functools import partial
import time
import psutil



logger = logging.getLogger(__name__)


async def run_hard_processes():
    from app.modules.wb_adv_updater import hard_ml_data_updater_process as hard_data_manager
    await asyncio.gather(hard_data_manager.run_update_data_in_neo4j())




run_own_process_list = [
     run_hard_processes,
     keywords_parsing_process,
     run_update_vectors_in_redis,
     run_update_minus_keywords_on_wb,
     run_update_keyword_stat,
     run_bidder_process,
     update_all_data_in_db,
      parser_all_white_phrase,
     run_main_coroutines,
     run_update_predict_ctr,
     run_update_model


]


def process_controller(process_pids: list[int], process_names: list[str]):
    time.sleep(10)
    while True:
        for pid, name in zip(process_pids, process_names):
            logger.debug(f'Проверка процесса: {name}')
            try:
                proc = psutil.Process(pid)
            except psutil.NoSuchProcess:
                logger.error(f'Процесс с PID {pid} (имя: {name}) не существует.')
                continue

            logger.debug(f'Создан объект процесса: {name}')
            memory_usage = proc.memory_info().rss / (1024 * 1024)
            logger.debug('Получили использование памяти')
            process_info = {
                'PID': pid,
                'Name': name,
                'Memory Usage (MB)': memory_usage,
                'Status': proc.status(),
                'Threads': proc.num_threads(),
                'Create Time': time.ctime(proc.create_time()),
                'Open Files': len(proc.open_files())
            }

            info_str = (
                f"Process Info:\n"
                f"  PID: {process_info['PID']}\n"
                f"  Name: {process_info['Name']}\n"
                f"  CPU Usage (%): {process_info['CPU Usage (%)']:.2f}\n"
                f"  Memory Usage (MB): {process_info['Memory Usage (MB)']:.2f}\n"
                f"  Status: {process_info['Status']}\n"
                f"  Threads: {process_info['Threads']}\n"
                f"  Create Time: {process_info['Create Time']}\n"
                f"  Open Files: {process_info['Open Files']}\n")

            logger.info(info_str)
            logger.debug(f'Проверка жив ли процесс: {name}')
            if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                logger.error(f'Процесс мертв, перезапуск процесса: {name}')
        time.sleep(60)



def run_coroutines(coroutine):
    asyncio.run(coroutine())


def main():
    processes = []
    process_pids = []
    process_names = []

    for run_own_process in run_own_process_list:
        func = partial(run_coroutines, run_own_process)
        process = Process(target=func, name=run_own_process.__name__)
        process.start()
        logger.info(f'Запущен процесс {process.pid} - {run_own_process.__name__}')
        processes.append(process)
        process_pids.append(process.pid)
        process_names.append(run_own_process.__name__)

    # Запуск process_controller в отдельном процессе
    controller_process = Process(target=process_controller, args=(process_pids, process_names), name='ProcessController')
    controller_process.start()
    logger.info(f'Запущен процесс-контроллер с PID {controller_process.pid}')

    for process in processes:
        process.join()
    controller_process.join()
    return None



if __name__ == '__main__':

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
            continue  # Продолжение работы программы после других исключений
