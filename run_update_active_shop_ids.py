import dotenv

dotenv.load_dotenv()
from python_modules.logger import setup_logging

setup_logging()

import asyncio

from app.modules.shop_runner.shop_run_worker.update_active_shop_ids_in_redis import (
    run_shop_ids_update,
)

if __name__ == "__main__":
    asyncio.run(run_shop_ids_update())
