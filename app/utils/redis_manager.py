import asyncio
import datetime
import json
from typing import Union

import redis

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting, WBItemPosition

redis_client = redis.asyncio.Redis(host='localhost', port=6379, db=0)


class RedisEvent(asyncio.Event):
    def __init__(self, key=None):
        if key:
            self.key = key
        else:
            self.key = 'event:' + str(id(self))
        super().__init__()

    async def _get_redis(self):
           return redis_client

    async def set(self):
        redis = await self._get_redis()
        await redis.set(self.key, 1)
        super().set()

    async def clear(self):
        redis = await self._get_redis()
        await redis.delete(self.key)
        super().clear()

    async def wait(self):
        redis = await self._get_redis()
        while True:
            result = await redis.get(self.key)
            if result:
                break
            await asyncio.sleep(0.1)
        await super().wait()

    async def is_set(self):
        redis = await self._get_redis()
        result = await redis.get(self.key)
        return result is not None






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


async def add_positions_to_redis(positions: list[WBItemPosition]):
    base_key = 'adv_positions'
    for position in positions:
       key = f'{base_key}:{position.keyword.text}:{position.nmid}'
       # real_position = position.real_position
       # promo_position =  position.promo_position
       # base_position = position.base_position
       # text = position.keyword.text
       # cpm = position.cpm
       # adv_id = position.adv_id
       # nmid = position.nmid
       position_dict = position.to_dict()
       await redis_client.set(key, json.dumps(position_dict))

async def read_position_from_redis(keyword: str, nmid: int):
    base_key = f'adv_positions:{keyword}:{nmid}'
    json_data = await redis_client.get(base_key)
    if not json_data:
        return None
    position = WBItemPosition.from_dict(json.loads(json_data))
    return position


async def get_keywords_positions(adv_setting, texts):
    positions = []
    for text in texts:
        key = 'adv_positions:' + text + ':' + str(adv_setting.nmids[0])
        json_data = await redis_client.get(key)
        if not json_data:
            continue
        position = WBItemPosition.from_dict(json.loads(json_data))
        positions.append(position)
    return positions


async def set_position_to_out_index(position):
    position_out_index = WBItemPosition()
    position_out_index.real_position = 0
    position_out_index.base_position = 0
    position_out_index.promo_position = 0
    position_out_index.keyword = position.keyword
    position_out_index.adv_id = position.adv_id
    position_out_index.nmid = position.nmid
    position_out_index.cpm = None
    await add_positions_to_redis([position_out_index])