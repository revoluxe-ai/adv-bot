from app.modules.wb_adv_updater.runner import run_main_process as main_loop, run_update_model
from python_modules.logger import setup_logging
import logging
import asyncio
from multiprocessing import Process


def run_main_coroutines():
    asyncio.run(main_loop())





def main():
    common_process = Process(target=run_main_coroutines)
    common_process.start()
    process_update_model = Process(target=run_update_model)
    process_update_model.start()
    common_process.join()
    process_update_model.join()
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
