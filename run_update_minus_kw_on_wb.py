from time import sleep

from app.modules.wb_adv_updater.runner import Runner
from app.utils.redis_manager import RedisEvent
import logging

logger = logging.getLogger(__name__)


import asyncio
from app import settings
predicted = RedisEvent(key='predicted')

runner = Runner()

max_sql_thread = settings.MAX_MINUS_KW_THREAD

semaphore = asyncio.Semaphore(max_sql_thread)

if __name__ == '__main__':
    while True:
        try:
            asyncio.run(runner.run_update_all_keywords_on_wb(semaphore))
        except Exception as e:
            logger.exception(e)
            sleep(70)

