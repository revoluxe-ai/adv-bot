import asyncio

from auto_adv_master.client_bot.client_bot import run
from python_modules.logger import setup_logging

setup_logging()



if __name__ == "__main__":
    asyncio.run(run())

