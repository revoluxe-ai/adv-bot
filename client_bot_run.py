import asyncio
from app import client_bot
from python_modules.logger import setup_logging
setup_logging()



if __name__ == "__main__":
    asyncio.run(client_bot.run())

