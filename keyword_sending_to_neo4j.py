import dotenv

from python_modules.logger import setup_logging

dotenv.load_dotenv()
from app.modules.wb_adv_updater import ml_data_manager
import logging
import asyncio

setup_logging()

logger = logging.getLogger(__name__)



if __name__ == '__main__':
    asyncio.run(ml_data_manager.update_wb_adv_phrase_in_neo4j())