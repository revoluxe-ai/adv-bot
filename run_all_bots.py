
import app
import asyncio
from python_modules.logger import setup_logging
setup_logging()


async def run_all():
    await asyncio.gather(
        app.admin_bot.run(),
        app.client_bot.run()

    )




if __name__ == "__main__":
    asyncio.run(run_all())



