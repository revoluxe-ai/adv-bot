import os

import redis

redis_host = os.environ.get("REDIS_HOST")


redis_client = redis.asyncio.Redis(host=redis_host, port=6379, db=0)
