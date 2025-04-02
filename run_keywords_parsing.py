import asyncio
import dotenv
dotenv.load_dotenv()
from app.modules.wb_adv_updater.runner import keywords_parsing_process
from python_modules.logger import setup_logging

setup_logging()




if __name__ == '__main__':
    asyncio.run(keywords_parsing_process())