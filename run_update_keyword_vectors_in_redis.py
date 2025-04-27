import asyncio

from app.utils.NeoDataScience.driver import DataScience
from python_modules.logger import setup_logging

setup_logging()


gds = DataScience()


if __name__ == "__main__":
    asyncio.run(gds.update_keywords_vectors_process())
