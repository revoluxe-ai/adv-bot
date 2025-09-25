import os

import redis
from typing import cast

redis_host = os.environ.get("REDIS_HOST")


redis_client = redis.asyncio.Redis(host=cast(str, redis_host), port=6379, db=0)
