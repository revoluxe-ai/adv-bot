from app.modules.wb_adv_updater.runner import Runner
from app.utils.redis_manager import RedisEvent

import asyncio
from app import settings
predicted = RedisEvent(key='predicted')

runner = Runner()

max_sql_thread = settings.MAX_MINUS_KW_THREAD

semaphore = asyncio.Semaphore(max_sql_thread)

if __name__ == '__main__':
    asyncio.run(runner.run_update_minus_keywords_on_wb(semaphore))
