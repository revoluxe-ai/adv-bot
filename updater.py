from app.modules.wb_adv_updater.runner import (
                                               run_update_model,
                                               run_update_data_in_neo4j,
                                               run_main_coroutines,
                                                  keywords_parsing_process,
                                                  run_update_vectors_in_redis,
                                                    run_update_predict_ctr,
                                                     run_update_minus_keywords_on_wb
)
from python_modules.logger import setup_logging
import logging
import asyncio
from multiprocessing import Process
from functools import partial




run_own_process_list = [
     run_main_coroutines,
     run_update_model,
     run_update_data_in_neo4j,
     keywords_parsing_process,
     run_update_vectors_in_redis,
     run_update_minus_keywords_on_wb


]

def run_coroutines(coroutine):
    asyncio.run(coroutine())


def main():
    processes = []
    for run_own_process in run_own_process_list:
        func = partial(run_coroutines, run_own_process)
        process = Process(target=func)
        process.start()
        processes.append(process)
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
