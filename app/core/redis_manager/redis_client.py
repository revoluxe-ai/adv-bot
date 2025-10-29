import os

from redis.asyncio import Redis

from app.settings import settings

redis_host = os.environ.get("REDIS_HOST")
assert redis_host is not None, "REDIS_HOST environment variable not set"

redis_client = Redis(host=redis_host, port=settings.REDIS_PORT, db=0)
