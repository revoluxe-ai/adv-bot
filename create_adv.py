import dotenv
from aiohttp import ClientSession

dotenv.load_dotenv()
from app.client_bot.bot import get_bot
from python_modules.logger import setup_logging

dotenv.load_dotenv()
import asyncio

from app.modules.adv_creator.backend.tasks import create_complex_advs

setup_logging()
shop_id: str = ...


nmid: int = ...


async def create_complex_adv():
    async with ClientSession() as client_session:
        bot = get_bot()
        ctx = {"bot": bot, "client_session": client_session}

        await create_complex_advs(ctx, nmid, shop_id, False, 373435337)


if __name__ == "__main__":
    asyncio.run(create_complex_adv())
