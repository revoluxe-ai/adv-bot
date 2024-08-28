import asyncio
from time import sleep

from app.modules.wb_adv_updater.runner import Runner
import logging

logger = logging.getLogger(__name__)
runner = Runner()


semaphore = asyncio.Semaphore(50)

if __name__ == '__main__':
    while True:
        try:
            asyncio.run(runner.keywords_parsing_process(semaphore))
        except Exception as exc:
            logger.error(f'Error in run_keywords_parsing: {exc}')
            sleep(60)
