from cashews import cache

from app.settings import settings


def setup_redis_cache() -> None:
    redis_host = settings.REDIS_MASTER_HOST
    redis_port = settings.REDIS_PORT
    redis_db = 0
    redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
    cache.setup(redis_url)

