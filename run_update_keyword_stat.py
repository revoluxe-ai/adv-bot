from app.modules.wb_adv_updater.runner import Runner
from app.utils.redis_manager import RedisEvent

predicted = RedisEvent(key='predicted')

runner = Runner()


if __name__ == '__main__':
    import asyncio
    asyncio.run(runner.run_update_keyword_stat(predicted))