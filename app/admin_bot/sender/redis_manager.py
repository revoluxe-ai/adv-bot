import redis


_redis_db = redis.asyncio.Redis(host='localhost', port=6379, db=5)


def _get_dhash_key(dhash: str):
    return f'telegram_file_dhash:{dhash}'


async def set_file_telegram_file(dhash: str, file_telegram_id: int):
    await _redis_db.set(_get_dhash_key(dhash), file_telegram_id)


async def get_telegram_file(dhash: str):
    return await _redis_db.get(_get_dhash_key(dhash))


async def set_message_send(message_hash: str, chat_id: int):
    element = str(chat_id) + message_hash
    return await _redis_db.sadd('send_telegram_messages', element)


async def check_message_send(message_hash: str, chat_id: int):
    element = str(chat_id) + message_hash
    return await _redis_db.sismember('send_telegram_messages', element)


