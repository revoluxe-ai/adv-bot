import asyncio
import datetime
import json
import typing
from types import NoneType
from typing import Union
import logging

from app.utils import text_cleaner

logger = logging.getLogger(__name__)

import redis

from app.modules.keywords_query import keywords_query
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
    logger.debug('Получение прав на токен из Redis')
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
        if not keyword.query:
            query = keywords_query.get_queries_of_keyword(keyword.text)
            keyword.query = query
        keywords.append(keyword)

    return keywords


async def add_positions_to_redis(positions: list[WBItemPosition]):
    base_key = 'adv_positions'
    for position in positions:
       position.timestamp = datetime.datetime.now()
       key = f'{base_key}:{position.keyword_text}:{position.nmid}'
       position_dict = position.to_dict()
       await redis_client.set(key, json.dumps(position_dict))

async def get_keyword_position(keyword: str, nmid: int)->Union[WBItemPosition, None]:
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
        if position:
            position.keyword_text = text
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


async def set_predict_ctr(adv_id, keyword, predict_ctr):
    key = f'predict_ctr:{adv_id}:{keyword}'
    await redis_client.set(key, predict_ctr)


async def get_predict_ctr(adv_id, keyword):
    key = f'predict_ctr:{adv_id}:{keyword}'
    predict_ctr_bytes = await redis_client.get(key)
    if predict_ctr_bytes is None:
        return None
    predict_ctr_str = predict_ctr_bytes.decode('utf-8')
    predict_ctr = float(predict_ctr_str)
    return predict_ctr



async def set_block_position_status(keywordsetting_original_id: int,
                                    block_position_status: str,
                                    new_time: datetime) -> None:
    key = 'block_position_status:' + str(keywordsetting_original_id)
    value = block_position_status + ':' + str(new_time.timestamp())
    await redis_client.set(key, value)

async def get_block_position_status(keywordsetting_original_id: int) -> tuple[str, datetime]:
    key = 'block_position_status:' + str(keywordsetting_original_id)
    value = await redis_client.get(key)
    if value is None:
        return None
    value = value.decode('utf-8')
    block_position_status, timestamp = value.split(':')
    timestamp = float(timestamp)
    timestamp = datetime.datetime.fromtimestamp(timestamp)
    return block_position_status, timestamp


async def set_item_vector(nmid: int, vector: list[float]) -> None:
    key = 'item_vector:' + str(nmid)
    await redis_client.set(key, json.dumps(vector))


async def get_item_vector(nmid: int) -> list[float]:
    key = 'item_vector:' + str(nmid)
    vector_bytes = await redis_client.get(key)
    if vector_bytes is None:
        return None
    vector_str = vector_bytes.decode('utf-8')
    vector = json.loads(vector_str)
    return vector


async def set_keyword_vector(keyword: str, vector: list[float]) -> None:
    key = 'keyword_vector:' + keyword
    await redis_client.set(key, json.dumps(vector))

async def get_keyword_vector(keyword: str) -> list[float]:
    key = 'keyword_vector:' + keyword
    vector_bytes = await redis_client.get(key)
    if vector_bytes is None:
        return None
    vector_str = vector_bytes.decode('utf-8')
    vector = json.loads(vector_str)
    return vector




async def get_keywords_vectors(keywords)->list[tuple[str, list[float]]]:
    vectors = []
    for keyword in keywords:
       vector = await get_keyword_vector(keyword)
       if vector:
              vectors.append((keyword, vector))
    return vectors



async def get_nmid_vectors(nmids_batch: list[int]) -> list[tuple[int, list[float]]]:
    vectors = []
    for nmid in nmids_batch:
        vector = await get_item_vector(nmid)
        if vector:
            vectors.append((nmid, vector))
    return vectors


async def check_phrase_in_neo(hash_text):
    key = 'phrase_in_neo:' + str(hash_text)
    answer = await redis_client.get(key)
    if answer is None:
        return False
    return True


async def add_phrase_hash_like_is_in_neo(hash_text):
    key = 'phrase_in_neo:' + str(hash_text)
    await redis_client.set(key, 1)
    return None


async def get_black_phrases(advsetting_id):
    key = 'black_phrases:' + str(advsetting_id)
    answer = await redis_client.get(key)
    if answer == b'' or not answer:
        return []
    answer = answer.decode('utf-8')
    answer = answer.split(',')
    return answer

async def set_black_phrases(advsetting_id, black_phrases: list[str]):
    key = 'black_phrases:' + str(advsetting_id)
    black_phrases = ','.join(black_phrases)
    await redis_client.set(key, black_phrases)
    return None


async def set_keyword_cluster(keyword: str, cluster_name: str):
    keyword = text_cleaner.clear(keyword)
    key = 'keyword_cluster:' + keyword
    await redis_client.set(key, cluster_name)
    return None


async def get_cluster_name(text):
    text = text_cleaner.clear(text)
    key = 'keyword_cluster:' + text
    answer = await redis_client.get(key)
    if answer is None:
        return None
    return answer.decode('utf-8')


async def get_all_cluster_names()-> set[str]:
    pattern = 'keyword_cluster:*'
    keys = await redis_client.keys(pattern)
    cluster_names = set()
    for key in keys:
        name = await redis_client.get(key)
        if name is not None:
            cluster_names.add(name.decode('utf-8'))
    return cluster_names


async def get_keys(pattern):
    keys = await redis_client.keys(pattern)
    return keys


async def get(key):
    value = await redis_client.get(key)
    return value


async def set_cluster_and_preset(text, cluster: typing.Optional[str], preset:  typing.Optional[int]):
    key = 'cluster_and_preset:' + text
    if cluster is None or preset is None:
        await redis_client.delete(key)
    else:
        value = cluster + ':' + str(preset)
        await redis_client.set(key, value)
    return None




async def get_cluster_and_preset(text)-> (str, int,):
    key = 'cluster_and_preset:' + text
    value = await redis_client.get(key)
    if isinstance(value, NoneType):
        return None, None
    value = value.decode('utf-8')
    data = value.split(':')
    try:
        cluster, preset = data
        return cluster, preset
    except Exception:
        logger.error('Не удалось получить кластер и пресет из значения: ' + value)
        await set_cluster_and_preset(text, None, None)
        return None, None



async def get_nmid(adv_id):
    key = 'adv_nmid:' + str(adv_id)
    nmid = await redis_client.get(key)
    if nmid is None:
        return None
    return int(nmid)


async def set_nmid(adv_id, nmid):
    key = 'adv_nmid:' + str(adv_id)
    await redis_client.set(key, nmid)
    return None


async def set_keyword_send_status(cluster_name, nmid, status: str):
    key = 'keyword_send_status:' + cluster_name + ':' + str(nmid)
    await redis_client.set(key, status)
    return None


async def get_keyword_send_status(cluster_name: str, nmid: int) -> str:
    key = 'keyword_send_status:' + cluster_name + ':' + str(nmid)
    status = await redis_client.get(key)
    return status