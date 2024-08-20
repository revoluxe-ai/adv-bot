from threading import Thread
from app.modules.wb_adv_updater.runner import (
                                               run_update_data_in_neo4j,
                                               run_main_coroutines,
                                               keywords_parsing_process,
                                               run_update_vectors_in_redis,
                                               run_update_minus_keywords_on_wb,
                                               run_update_keyword_stat,
                                               run_bidder_process,
                                               update_all_data_in_db,
                                                parser_all_white_phrase
)
from python_modules.logger import setup_logging
import logging
import asyncio
from multiprocessing import Process
from functools import partial
import os
import time
import psutil



logger = logging.getLogger(__name__)


run_own_process_list = [
     run_main_coroutines,
     run_update_data_in_neo4j,
     keywords_parsing_process,
     run_update_vectors_in_redis,
     run_update_minus_keywords_on_wb,
     run_update_keyword_stat,
     run_bidder_process,
     update_all_data_in_db,
      parser_all_white_phrase


]


def process_controller(processes: list[Process]):
    time.sleep(1)
    while True:
        for process in processes:
            logger.debug(f'Проверка процесса: {process.name}')
            proc = psutil.Process(process.pid)
            logger.debug(f'Создан объект процесса: {process.name}')
            # Получаем использование CPU и памяти
            # cpu_usage = proc.cpu_percent(interval=1)
            logger.debug('Получили процент использования cpu')# Процент использования CPU за 1 секунду
            memory_usage = proc.memory_info().rss / (1024 * 1024)
            logger.debug('Получили использование памяти')# Использование памяти в МБ
            process_info = {
                'PID': process.pid,
                'Name': process.name,
                # 'CPU Usage (%)': cpu_usage,
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
                # f"  CPU Usage (%): {process_info['CPU Usage (%)']:.2f}\n"
                f"  Memory Usage (MB): {process_info['Memory Usage (MB)']:.2f}\n"
                f"  Status: {process_info['Status']}\n"
                f"  Threads: {process_info['Threads']}\n"
                f"  Create Time: {process_info['Create Time']}\n"
                f"  Open Files: {process_info['Open Files']}\n")


            logger.info(info_str)
            logger.debug(f'Проверка жив ли процесс: {process.name}')
            live_process = process.is_alive()
            logger.debug(f'Проверка завершена: {process.name}')
            if not live_process:
                logger.error(f'Процесс мертв, перезапуск процесса: {process.name}')
                process.start()
                logger.info(f'Процесс перезапущен: {process.name}')
        time.sleep(60)

def run_coroutines(coroutine):
    asyncio.run(coroutine())


def main():
    processes = []
    for run_own_process in run_own_process_list:
        func = partial(run_coroutines, run_own_process)
        process = Process(target=func, name=run_own_process.__name__)
        process.start()
        logger.info(f'Запущен процесс {process.pid} - {run_own_process.__name__}')
        processes.append(process)
    thread_control = Thread(target=process_controller, args=(processes,))
    thread_control.start()
    thread_control.join()
    for process in processes:
        process.join()
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
