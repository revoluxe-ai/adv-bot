from app.modules.wb_adv_updater.runner import Runner
from python_modules.logger import setup_logging
import logging


r = Runner()
if __name__ == '__main__':
    level = logging.INFO
    setup_logging()
    while True:
        try:
            r.run(debug_mode = False)
            break
        except InterruptedError:
            raise
        except:
            continue
