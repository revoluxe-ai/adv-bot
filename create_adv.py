import dotenv
dotenv.load_dotenv()
from app.client_bot.bot import get_bot
from python_modules.logger import setup_logging

dotenv.load_dotenv()
from app.modules.adv_creator.backend.tasks import create_complex_advs
import asyncio

setup_logging()
shop_id = '79a685e7-c7bd-4447-bae1-d9935787de3d'


nmid = 38157677


bot =  get_bot()


ctx = {
    'bot': bot
}

async def create_complex_adv():
    await create_complex_advs(
        ctx,
        nmid,
        shop_id,
        False,
        373435337

    )




if __name__ == '__main__':
    asyncio.run(create_complex_adv())
