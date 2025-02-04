import dotenv
dotenv.load_dotenv()

from python_modules.logger import setup_logging
setup_logging()

import asyncio
from app.client_bot.client_bot import run



if __name__ == "__main__":
    asyncio.run(run())
