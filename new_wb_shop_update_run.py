from time import sleep

import dotenv

from app.modules.shop_runner.exceptions import ShopRunnerCriticalError

dotenv.load_dotenv()
from app.modules.shop_runner import run_process_func
from python_modules.logger import setup_logging

setup_logging()
import logging


logger = logging.getLogger(__name__)

if __name__ == "__main__":
    while True:
        try:
            run_process_func.run()
        except ShopRunnerCriticalError as e:
            raise e
        except Exception as e:
            logger.error(
                f"Ошибка точки входа Нового Апдейтера магазинов {e}", exc_info=True
            )
            sleep(5)
