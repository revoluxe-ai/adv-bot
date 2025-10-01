import dotenv

dotenv.load_dotenv()
from python_modules.logger import setup_logging

setup_logging()

# Ensure models that define SQLAlchemy mapped classes are imported early so
# SQLAlchemy can resolve string-based relationships at runtime.
# The AdvPayment model used across the project is defined in app.modules.billing.models
# — import it here to avoid KeyError: 'AdvPayment' during model registry resolution.
import app.modules.billing.models  # noqa: F401

import asyncio

from app.modules.shop_runner.shop_run_worker.update_active_shop_ids_in_redis import (
    run_shop_ids_update,
)

if __name__ == "__main__":
    asyncio.run(run_shop_ids_update())
