import os

from redis.asyncio import Redis

from app.settings import settings

redis_host = os.environ.get("REDIS_HOST")

redis_client = Redis(host=redis_host, port=settings.REDIS_PORT, db=0)
