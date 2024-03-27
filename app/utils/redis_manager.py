import redis
import datetime


redis_client = redis.asyncio.Redis(host='localhost', port=6379, db=0)







async def set_token_rights(hash_token, timeout):
    # now = datetime.datetime.now()
    # expire = now + datetime.timedelta(seconds=timeout)

    await redis_client.set('token_rights:' + str(hash_token), 'True', ex = timeout)
    return None


async def get_token_rights(hash_token):
    answer = await redis_client.get('token_rights:'  + str(hash_token))
    return answer