import redis.asyncio

# Заглушка для примера, замените параметры на ваши реальные
redis_replica_client = redis.asyncio.StrictRedis(
    host="localhost", port=6379, db=0
)

