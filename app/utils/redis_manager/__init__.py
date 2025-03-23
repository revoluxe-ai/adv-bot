import asyncio
import datetime
import json
import time
import typing
from types import NoneType
from typing import Union
import logging

from app.modules.full_stat_adv_updater.types import FullAdvStat
from app.utils import text_cleaner
from app.utils.redis_manager.exc import DataNotFoundError

logger = logging.getLogger(__name__)

import redis

from app.modules.keywords_query import keywords_query
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting, WBItemPosition
import os
from urllib.parse import quote, unquote
from app import settings




redis_host_master = settings.REDIS_MASTER_HOST
redis_master_client = redis.asyncio.StrictRedis(host=redis_host_master, port=6379, db=0)

redis_host_replica = settings.REDIS_REPLICA_HOST
redis_replica_client = redis.asyncio.StrictRedis(host=redis_host_replica, port=6379, db=0)



def encode_key(raw_key):
    encoded_key = quote(raw_key)
    return encoded_key

def decode_key(key):
    decoded_key = unquote(key)
    return decoded_key


class RedisEvent(asyncio.Event):
    def __init__(self, key=None):
        if key:
            self.key = key
        else:
            self.key = 'event:' + str(id(self))
        super().__init__()

    @staticmethod
    async def _get_redis(type: str = 'read'):
        if type == 'read':
            return redis_replica_client
        elif type == 'white':
            return redis_master_client


    async def set(self):
        redis = await self._get_redis('white')
        await redis.set(self.key, 1)
        super().set()

    async def clear(self):
        redis = await self._get_redis('white')
        await redis.delete(self.key)
        super().clear()

    async def wait(self):
        redis = await self._get_redis('read')
        while True:
            result = await redis.get(self.key)
            if result:
                break
            await asyncio.sleep(0.1)
        await super().wait()

    async def is_set(self):
        redis = await self._get_redis('read')
        result = await redis.get(self.key)
        return result is not None


async def set_token_rights(hash_token, timeout):
    # now = datetime.datetime.now()
    # expire = now + datetime.timedelta(seconds=timeout)

    await redis_master_client.set('token_rights:' + str(hash_token), 'True', ex = timeout)
    return None


async def get_token_rights(hash_token):
    logger.debug('Получение прав на токен из Redis')
    answer = await redis_replica_client.get('token_rights:'  + str(hash_token))
    return answer



async def set_check_last_24_hours(adv_original_id):
    await redis_master_client.set('check_adv_last_24_hours:' + str(adv_original_id), 'True', ex = 60*60*24)


async def check_last_24_hours(adv_original_id):
    answer = await redis_replica_client.get('check_adv_last_24_hours:' + str(adv_original_id))
    return answer


async def set_auto_block_statuses(new_statuses: list[tuple[int, bool]]):
    data = {
        f'auto_block_status:{keywordsetting_original_id}': 1 if auto_block_status else 0
        for keywordsetting_original_id, auto_block_status in new_statuses
    }
    if data:
        await redis_master_client.mset(data)


async def set_auto_block_status(keywordsetting_original_id: int, auto_block_status: bool) -> None:
    key = 'auto_block_status:' + str(keywordsetting_original_id)
    if auto_block_status is True:
        await redis_master_client.set(key, 1)
    else:
        await redis_master_client.set(key, 0)
    return None


async def get_auto_block_status(keywordsetting_original_id: int) -> bool:
    key = 'auto_block_status:' + str(keywordsetting_original_id)
    answer = await redis_replica_client.get(key)
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
    await redis_master_client.set(key, json_data, ex=cache_timeout)



async def get_keyword_statistics(adv_setting: AdvSetting, pass_time: Union[int, None]) -> Union[list[CalculatedKeyword], None]:
    if not pass_time:
        pass_time = 0
    key = 'adv_keyword_statistics:' + str(adv_setting.id) + ':' + str(pass_time)

    json_data = await redis_replica_client.get(key)
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


async def add_positions_to_redis(positions: list[WBItemPosition]) -> None:
    base_key = 'adv_positions'
    for position in positions:
       position.timestamp = datetime.datetime.now()
       key = f'{base_key}:{position.keyword_text}:{position.nmid}'
       position_dict = position.to_dict()
       await redis_master_client.set(key, json.dumps(position_dict))

async def get_keyword_position(keyword: str, nmid: int)->Union[WBItemPosition, None]:
    base_key = f'adv_positions:{keyword}:{nmid}'
    json_data = await redis_replica_client.get(base_key)
    if not json_data:
        cluster, _ = await get_cluster_and_preset(keyword)
        if not cluster:
            return None
        base_key = f'adv_positions:{cluster}:{nmid}'
        json_data = await redis_replica_client.get(base_key)
        if not json_data:
            return None
        else:
            position = WBItemPosition.from_dict(json.loads(json_data))
            return position
    position = WBItemPosition.from_dict(json.loads(json_data))
    return position


async def get_keywords_positions(adv_setting, texts):
    keys = ['adv_positions:' + text + ':' + str(adv_setting.nmid[0]) for text in texts]
    results = await redis_replica_client.mget(keys)
    positions = []
    missing_texts = []

    for text, json_data in zip(texts, results):
        if json_data:
            position = WBItemPosition.from_dict(json.loads(json_data))
            position.keyword_text = text
            positions.append(position)
        else:
            missing_texts.append(text)

    if missing_texts:
        cluster_keys = []
        cluster_map = {}

        for text in missing_texts:
            cluster, _ = await get_cluster_and_preset(text)
            if cluster:
                key = 'adv_positions:' + cluster + ':' + str(adv_setting.nmid[0])
                cluster_keys.append(key)
                cluster_map[key] = text

        if cluster_keys:
            cluster_results = await redis_replica_client.mget(cluster_keys)

            for key, json_data in zip(cluster_keys, cluster_results):
                if json_data:
                    position = WBItemPosition.from_dict(json.loads(json_data))
                    position.keyword_text = cluster_map[key]
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
    key = f'predict_ctr:{adv_id}:{text_cleaner.clear(keyword)}'
    await redis_master_client.set(key, predict_ctr)


async def get_adv_id_to_text_predict_ctr_dict(adv_id: int, texts: list[str]) -> dict[str, float]:
    # Шаблон для поиска всех ключей, связанных с данным adv_id
    keys = [f'predict_ctr:{adv_id}:{text_cleaner.clear(keyword)}' for keyword in texts]

    # Получаем все значения за один запрос
    values = await redis_replica_client.mget(keys)

    # Собираем результат
    result = {}
    for keyword, value in zip(texts, values):
        if value is not None:
            try:
                result[keyword] = float(value.decode('utf-8'))
            except (ValueError, AttributeError):
                continue

    return result


async def get_predict_ctr(adv_id: int, keyword: str):
    keyword = text_cleaner.clear(keyword)
    key = f'predict_ctr:{adv_id}:{keyword}'
    try:
        predict_ctr_bytes = await redis_replica_client.get(key)
    except Exception as exc:
        raise exc

    if predict_ctr_bytes is None:
        return None
    predict_ctr_str = predict_ctr_bytes.decode('utf-8')
    predict_ctr = float(predict_ctr_str)
    return predict_ctr


async def set_predict_ctrs(adv_id, keywords: list[CalculatedKeyword]) -> list[CalculatedKeyword]:
    """
    Получить предсказанные CTR для списка пар (adv_id, keyword).

    :param adv_id: Идентификатор рекламной кампании.
    :param keywords: Список объектов CalculatedKeyword.
    :return: Список объектов CalculatedKeyword с обновленными предсказанными CTR.
    """
    # Формируем список ключей для запроса к Redis
    keys = [f'predict_ctr:{adv_id}:{text_cleaner.clear(keyword.text)}' for keyword in keywords]

    # Получаем данные из Redis за один запрос
    predict_ctr_bytes_list = await redis_replica_client.mget(keys)

    for i, keyword in enumerate(keywords):
        keyword.predict_ctr = predict_ctr_bytes_list[i]
    return keywords


async def set_block_position_status(keywordsetting_original_id: int,
                                    block_position_status: str,
                                    new_time: datetime) -> None:
    key = 'block_position_status:' + str(keywordsetting_original_id)
    value = block_position_status + ':' + str(new_time.timestamp())
    await redis_master_client.set(key, value)

async def get_block_position_status(keywordsetting_original_id: int) -> tuple[str, datetime] | None:
    key = 'block_position_status:' + str(keywordsetting_original_id)
    value = await redis_replica_client.get(key)
    if value is None:
        return None
    value = value.decode('utf-8')
    block_position_status, timestamp = value.split(':')
    timestamp = float(timestamp)
    timestamp = datetime.datetime.fromtimestamp(timestamp)
    return block_position_status, timestamp


async def set_item_vector(nmid: int, vector: list[float]) -> None:
    key = 'item_vector:' + str(nmid)
    await redis_master_client.set(key, json.dumps(vector))


async def get_item_vector(nmid: int) -> list[float] | None:
    key = 'item_vector:' + str(nmid)
    vector_bytes = await redis_replica_client.get(key)
    if vector_bytes is None:
        return None
    vector_str = vector_bytes.decode('utf-8')
    vector = json.loads(vector_str)
    return vector


async def set_keyword_vector(keyword: str, vector: list[float]) -> None:
    key = 'keyword_vector:' + keyword
    await redis_master_client.set(key, json.dumps(vector))


async def get_keyword_features_from_redis(keywords: list[str]) -> list[tuple[str, list[float]]]:
    if not keywords:
        return []
    keys = [f"keyword_vector:{keyword}" for keyword in keywords]

    # Получаем все вектора сразу с помощью MGET
    vectors_bytes = await redis_replica_client.mget(*keys)
    result = []
    for keyword in keywords:
        key = f"keyword_vector:{keyword}"
        vector_bytes = await redis_replica_client.get(key)
        if vector_bytes:
            vector_str = vector_bytes.decode('utf-8')
            vector = json.loads(vector_str)
            result.append((keyword, vector))

    return result




async def get_keyword_vector(keyword: str) -> typing.Optional[list[float]]:
    key = 'keyword_vector:' + keyword
    vector_bytes = await redis_replica_client.get(key)
    if vector_bytes is None:
        return None
    vector_str = vector_bytes.decode('utf-8')
    vector = json.loads(vector_str)
    return vector




async def get_keywords_vectors(keywords: list[str])->list[tuple[str, list[float]]]:
    vectors = await get_keyword_features_from_redis(keywords)
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
    answer = await redis_replica_client.get(key)
    if answer is None:
        return False
    return True


async def add_phrase_hash_like_is_in_neo(hash_text):
    key = 'phrase_in_neo:' + str(hash_text)
    await redis_master_client.set(key, 1)
    return None


async def get_black_phrases(advsetting_id):
    key = 'black_phrases:' + str(advsetting_id)
    answer = await redis_replica_client.get(key)
    if answer == b'' or not answer:
        return []
    answer = answer.decode('utf-8')
    answer = answer.split(',')
    return answer

async def set_black_phrases(advsetting_id, black_phrases: list[str]):
    key = 'black_phrases:' + str(advsetting_id)
    black_phrases = ','.join(black_phrases)
    await redis_master_client.set(key, black_phrases)
    return None


async def set_keyword_cluster(keyword: str, cluster_name: str):
    keyword = text_cleaner.clear(keyword)
    key = 'keyword_cluster:' + keyword
    await redis_master_client.set(key, cluster_name)
    return None


async def get_cluster_name(text):
    text = text_cleaner.clear(text)
    key = 'keyword_cluster:' + text
    answer = await redis_replica_client.get(key)
    if answer is None:
        return None
    return answer.decode('utf-8')


#функция не работает и не используется
# async def get_all_keywords_positions(text) -> list[WBItemPosition]:
#     key_pattern = f'adv_positions:{text}:*'
#     cursor = 0
#     positions = []
#
#     while True:
#         # Используем scan для поиска ключей
#         cursor, keys = await redis_replica_client.scan(cursor=cursor, match=key_pattern)
#
#         # Получаем данные по всем ключам за один запрос с использованием mget
#         if keys:
#             json_data_list = await redis_replica_client.mget(*keys)
#
#             for json_data in json_data_list:
#                 if json_data:
#                     position = WBItemPosition.from_dict(json.loads(json_data))
#                     positions.append(position)
#
#         # Если курсор вернулся в 0, значит, все ключи обработаны
#         if cursor == 0:
#             break
#
#     return positions


async def get_keys(pattern):
    cursor = b'0'
    keys = []

    while cursor != b'0':  # Ожидаем, пока курсор не вернется к начальной позиции
        cursor, batch = await redis_replica_client.scan(cursor, match=pattern)
        keys.extend(batch)

    return keys


async def get_all_cluster_names() -> set[str]:
    pattern = 'keyword_cluster:*'
    cursor = 0
    cluster_names = set()

    while True:
        # Используем scan для поиска ключей с шаблоном
        cursor, keys = await redis_replica_client.scan(cursor=cursor, match=pattern)

        if keys:
            # Получаем все значения для найденных ключей за один запрос
            values = await redis_replica_client.mget(*keys)

            for value in values:
                if value:
                    cluster_names.add(value.decode('utf-8'))

        # Если курсор вернулся в 0, значит, все ключи обработаны
        if cursor == 0:
            break

    return cluster_names


async def get(key):
    value = await redis_replica_client.get(key)
    return value


async def set_cluster_and_preset(text, cluster: str, preset:  typing.Optional[int]):
    key = 'cluster_and_preset:' + encode_key(text)
    if cluster is None or preset is None:
        await redis_master_client.delete(key)
    else:
        value = cluster + ':' + str(preset)
        await redis_master_client.set(key, value)
        text = cluster
        key = 'cluster_and_preset:' + encode_key(text)
        await redis_master_client.set(key, value)
    return None




async def get_cluster_and_preset(text)-> (str, int,):
    key = 'cluster_and_preset:' + encode_key(text)
    value = await redis_replica_client.get(key)
    if isinstance(value, NoneType):
        return None, None
    value = value.decode('utf-8')
    value = str(value)
    data = value.split(':')
    try:
        cluster, preset = data
    except:
        logger.error('Ошибка распаковки данных о кластере и пресете')
        return None, None
    return cluster, preset




async def get_nmid(adv_id):
    key = 'adv_nmid:' + str(adv_id)
    nmid = await redis_replica_client.get(key)
    if nmid is None:
        return None
    return int(nmid)


async def set_nmid(adv_id, nmid):
    key = 'adv_nmid:' + str(adv_id)
    await redis_master_client.set(key, nmid)
    return None


async def set_keyword_send_status(cluster_name, nmid, status: str):
    key = 'keyword_send_status:' + cluster_name + ':' + str(nmid)
    await redis_master_client.set(key, status)
    return None


async def get_keyword_send_status(cluster_name: str, nmid: int) -> str:
    key = 'keyword_send_status:' + cluster_name + ':' + str(nmid)
    status = await redis_replica_client.get(key)
    return status


async def set_last_views(adv_id: int, text: str, total_views: int):
    key = 'last_views:' + str(adv_id) + ':' + text
    await redis_master_client.set(key, total_views)
    return None


async def get_last_views(adv_id, text):
    key = 'last_views:' + str(adv_id) + ':' + text
    total_views = await redis_replica_client.get(key)
    if total_views is None:
        return None
    return int(total_views)


async def get_clusters_and_presets(texts: list[str]) -> dict[str, [tuple[str, int]]]:
    keys = [f'cluster_and_preset:{encode_key(text)}' for text in texts]
    values = await redis_replica_client.mget(keys)

    clusters_and_presets = {}

    for text, value in zip(texts, values):
        key = f'cluster_and_preset:{encode_key(text)}'

        if value is None:
            clusters_and_presets[text] = (None, None)
            continue

        value = value.decode('utf-8')
        try:
            cluster, preset = value.split(':')
            clusters_and_presets[text] = (cluster, int(preset))
        except Exception as e:
            logger.error(f'Ошибка при парсинге значения {value} из Redis с ключом {key}: {e}')
            clusters_and_presets[text] = (None, None)

    return clusters_and_presets


async def get_keywords_positions_by_nmid(nmid: int, texts: list[str]) -> list[WBItemPosition]:
    keys = [f'adv_positions:{text}:{nmid}' for text in texts]
    results = await redis_replica_client.mget(keys)
    positions = []
    for text, json_data in zip(texts, results):
        if json_data:
            position = WBItemPosition.from_dict(json.loads(json_data))
            position.keyword_text = text
            positions.append(position)
    return positions


async def set_full_stat_adv(adv_stats: typing.Iterable['FullAdvStat']):
    # Создаем словарь для ключей и значений
    data = {}
    for adv_stat in adv_stats:
        key = f'full_stat_adv:{adv_stat.advertId}'
        json_data = adv_stat.model_dump_json()
        data[key] = json_data

    # Используем mset для установки всех ключей за один запрос
    await redis_master_client.mget(data)

    return None


async def get_full_stat_adv(adv_id: int)-> str:
    key = f'full_stat_adv:{adv_id}'
    json_data = await redis_replica_client.get(key)
    if json_data is None:
        raise DataNotFoundError(f'Данные для объявления с adv_id={adv_id} не найдены в Redis')
    json_data = json_data.decode('utf-8')
    return json_data

async def set_last_full_stat_update(adv_id: int, last_update: datetime.datetime)-> None:
    key = f'last_full_stat_update:{adv_id}'
    await redis_master_client.set(key, last_update.timestamp())
    return None


async def get_last_full_stat_update(adv_id: int) -> typing.Optional[datetime.datetime]:
    key = f'last_full_stat_update:{adv_id}'
    value = await redis_replica_client.get(key)
    if value is None:
        return None
    value = value.decode('utf-8')
    value = float(value)
    return datetime.datetime.fromtimestamp(value)

async def set_max_bet_for_keyword(text: str, max_bet: int):
    key = f'max_bet:{text}'
    await redis_master_client.set(key, max_bet)

async def get_max_bet(text: str):
    key = f'max_bet:{text}'
    max_bet = await redis_replica_client.get(key)
    if max_bet is None:
        return None
    max_bet = int(max_bet)
    return max_bet


async def set_last_bid_update(adv_id: str):
    key = f'last_bid_update:{adv_id}'
    now = datetime.datetime.now()
    now = now.timestamp()
    await redis_master_client.set(key, now)


async def get_last_bid_update(adv_id) -> datetime:
    key = f'last_bid_update:{adv_id}'
    value = await redis_replica_client.get(key)
    value = datetime.datetime.fromtimestamp(value)
    return value



async def set_last_user_use_time(user_telegram_id: int):
    key = 'last_user_use_time:' + str(user_telegram_id)
    now = datetime.datetime.now()
    now = str(now.timestamp())
    await redis_master_client.set(key, now)

async def get_last_user_use_time(user_telegram_id: int):
    key = 'last_user_use_time:' + str(user_telegram_id)
    value = await redis_replica_client.get(key)
    if value is None:
        return None
    value = value.decode('utf-8')
    value = float(value)
    datetime_object = datetime.datetime.fromtimestamp(value)
    return datetime_object


async def get_last_users_use_time(user_telegram_ids: list[int]) -> list[float]:
    keys = ['last_user_use_time:' + str(user_telegram_id) for user_telegram_id in user_telegram_ids]
    values = await redis_replica_client.mget(keys)
    results = []
    for user_telegram_id, value in zip(user_telegram_ids, values):
        if value is None:
            results.append(None)
        else:
            value = value.decode('utf-8')
            value = float(value)
            results.append(value)
    return results


async def reset_last_user_use_time(telegram_user_id: int):
    key = 'last_user_use_time:' + str(telegram_user_id)
    await redis_master_client.delete(key)
    return None


async def get_last_adv_bid(adv_id: int) -> int | None:
    key = f'last_adv_bid:{adv_id}'
    value = await redis_replica_client.get(key)
    if not value:
        return None
    value = value.decode('utf-8')
    if value is None:
        return None
    return int(value)



async def set_last_adv_bid(adv_id: int, bid: int):
    key = f'last_adv_bid:{adv_id}'
    await redis_master_client.set(key, bid)


async def set_last_parsing_position_time(text: str, nmids: set[int]):
    time_now = time.time()
    pipeline = redis_master_client.pipeline()
    for nmid in nmids:
        key = f'last_start_parsing_position_time:{nmid}:{text}'  # Ключ включает nmid и text
        value = time_now
        await pipeline.set(key, value)
    await pipeline.execute()


async def get_last_parsing_position_time(text: str, nmid: int) -> int | None:
    key = f'last_start_parsing_position_time:{nmid}:{text}'  # Формируем ключ с nmid и text
    value = await redis_replica_client.get(key)
    if value is None:
        return None
    time_now = float(value.decode('utf-8'))  # Получаем time_now как float
    return int(time_now)  # Возвращаем время и текст

