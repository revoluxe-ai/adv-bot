import logging

from auto_adv_master.modules.wb_adv_updater.runner import Runner
from python_modules.logger import setup_logging

r = Runner()
if __name__ == '__main__':
    level = logging.INFO
    setup_logging()
    while True:
        # try:
        r.run(debug_mode=False)
        #     break
        # except KeyboardInterrupt:
        #     print("Программа остановлена пользователем.")
        #     break  # Выход из цикла, завершение программы
        # except InterruptedError:
        #     raise  # Перевыбрасывание исключения
        # except Exception as e:
        #     logging.error("Произошла ошибка:", exc_info=True)
        #     continue  # Продолжение работы программы после других исключений
