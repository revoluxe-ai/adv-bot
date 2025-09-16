import asyncio

import dotenv

dotenv.load_dotenv()
from python_modules.logger import setup_logging

setup_logging()
import logging

from app.modules.wb_adv_updater import ml_data_manager

logger = logging.getLogger(__name__)


async def update_cards():
    while True:
        try:
            await ml_data_manager.update_cards_in_graph_small_cycle()
        except Exception:
            logger.error("Ошибка обновления карточек в neo4j", exc_info=True)
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(update_cards())
