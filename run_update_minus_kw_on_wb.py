from app.modules.wb_adv_updater.runner import Runner
from app.utils.redis_manager import RedisEvent

import asyncio
from app import settings
predicted = RedisEvent(key='predicted')

runner = Runner()

max_sql_thread = settings.COUNT_THREAD_SQL_KW_STAT_LOAD

semaphore = asyncio.Semaphore(max_sql_thread)

if __name__ == '__main__':
    asyncio.run(runner.run_update_keyword_stat(predicted, semaphore))
