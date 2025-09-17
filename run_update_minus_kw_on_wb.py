import logging
from time import sleep

from aiohttp import ClientSession

from app.modules.wb_adv_updater.runner import Runner
from app.utils.redis_manager import RedisEvent

logger = logging.getLogger(__name__)


import asyncio

from app import settings

predicted = RedisEvent(key="predicted")


max_sql_thread = settings.MAX_MINUS_KW_THREAD

semaphore = asyncio.Semaphore(max_sql_thread)

if __name__ == "__main__":
    async with ClientSession() as client_session:
        runner = Runner(client_session)

        while True:
            try:
                asyncio.run(runner.run_update_all_keywords_on_wb(semaphore))
            except Exception as e:
                logger.exception(e)
                del e
                sleep(70)
