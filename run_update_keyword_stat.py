from app.modules.wb_adv_updater.runner import run_update_keyword_stat
from app.utils.redis_manager import RedisEvent
import logging

logger = logging.getLogger(__name__)

import asyncio
from app import settings
predicted = RedisEvent(key='predicted')

max_sql_thread = settings.COUNT_THREAD_SQL_KW_STAT_LOAD

semaphore = asyncio.Semaphore(max_sql_thread)

if __name__ == '__main__':
    while True:
        try:
            asyncio.run(run_update_keyword_stat())
        except Exception as e:
            logger.error(f'Ошибка в run_update_keyword_stat: {e}', exc_info=True)
            asyncio.sleep(60)
            continue