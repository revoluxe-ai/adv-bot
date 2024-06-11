import datetime
import json
from typing import Union

import redis

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting
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



async def set_auto_block_status(keywordsetting_original_id: int, auto_block_status: bool) -> None:
    key = 'auto_block_status:' + str(keywordsetting_original_id)
    if auto_block_status is True:
        await redis_client.set(key, 1)
    else:
        await redis_client.set(key, 0)
    return None


async def get_auto_block_status(keywordsetting_original_id: int) -> bool:
    key = 'auto_block_status:' + str(keywordsetting_original_id)
    answer = await redis_client.get(key)
    if answer is None:
        return False
    else:
        answer = int(answer)
    if answer == 0:
        auto_block_status = False
    else:
        auto_block_status = True
    return auto_block_status

async def set_keyword_statistics(adv_setting: AdvSetting,
                                 keywords: list[CalculatedKeyword],
                                 pass_time: Union[int, None],
                                 cache_timeout: int):
    if not pass_time:
        pass_time = 0
    key = 'adv_keyword_statistics:' + str(adv_setting.id) + ':' + str(pass_time)

    json_data = []

    for keyword in keywords:
        data = keyword.to_json()
        json_data.append(data)
    json_data = json.dumps(json_data)
    await redis_client.set(key, json_data, ex=cache_timeout)



async def get_keyword_statistics(adv_setting: AdvSetting, pass_time: Union[int, None]) -> Union[list[CalculatedKeyword], None]:
    if not pass_time:
        pass_time = 0
    key = 'adv_keyword_statistics:' + str(adv_setting.id) + ':' + str(pass_time)

    json_data = await redis_client.get(key)
    if not json_data:
        return None
    json_data = json.loads(json_data)

    keywords = []
    for row in json_data:
        keyword: CalculatedKeyword = CalculatedKeyword.from_json(row)
        keywords.append(keyword)

    return keywords





