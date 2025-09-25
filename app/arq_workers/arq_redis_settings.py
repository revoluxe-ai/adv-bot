from arq.connections import RedisSettings

from app.settings import settings

assert settings.REDIS_MASTER_HOST is not None
arq_redis_settings = RedisSettings(host=settings.REDIS_MASTER_HOST)
