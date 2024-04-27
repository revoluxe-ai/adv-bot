import asyncio

from app.client_bot.client_bot import run
from python_modules.logger import setup_logging

setup_logging()



if __name__ == "__main__":
    asyncio.run(run())

