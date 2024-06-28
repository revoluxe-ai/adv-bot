import asyncio

from app.modules.wb_adv_updater.runner import Runner

runner = Runner()

if __name__ == '__main__':
    asyncio.run(runner.keywords_parsing_process())