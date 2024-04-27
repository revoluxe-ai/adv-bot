import datetime

import redis

redis_client = redis.asyncio.Redis(host='localhost', port=6379, db=0)







async def set_token_rights(hash_token, timeout):
    # now = datetime.datetime.now()
    # expire = now + datetime.timedelta(seconds=timeout)

    await redis_client.set('token_rights:' + str(hash_token), 'True', ex = timeout)
    return None


async def get_token_rights(hash_token):
    answer = await redis_client.get('token_rights:'  + str(hash_token))
    return answer



async def set_check_last_24_hours(adv_original_id):
    await redis_client.set('check_adv_last_24_hours:' + str(adv_original_id), 'True', ex = 60*60*24)


async def check_last_24_hours(adv_original_id):
    answer = await redis_client.get('check_adv_last_24_hours:' + str(adv_original_id))
    return answer

