from arq.connections import RedisSettings

from app.settings import settings

arq_redis_settings = RedisSettings(
        host=settings.REDIS_MASTER_HOST
    )
