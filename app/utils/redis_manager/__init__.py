import asyncio
import datetime
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, cast
from urllib.parse import quote, unquote

import redis
from redis.asyncio.client import StrictRedis

from app.core.wb_api.data_classes.adv import Balances
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting, WBItemPosition
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.settings import settings

logger = logging.getLogger(__name__)

redis_master_client: StrictRedis = redis.asyncio.Redis(host="localhost", port=6379, db=0)
redis_replica_client: StrictRedis = redis.asyncio.Redis(host="localhost", port=6379, db=0)
redis_client = redis_master_client

def encode_key(raw_key: str) -> str:
    encoded_key = quote(raw_key)
    return encoded_key

def decode_key(key: str) -> str:
    decoded_key = unquote(key)
    return decoded_key


class RedisEvent(asyncio.Event):
    def __init__(self, key: str | None = None) -> None:
        if key:
            self.key = key
        else:
            self.key = "event:" + str(id(self))
        super().__init__()

    @staticmethod
    async def _get_redis(type: str = "read") -> StrictRedis:
        if type == "read":
            return redis_replica_client
        elif type == "white":
            return redis_master_client
        raise ValueError("Invalid redis type")

    def set(self) -> None:
        # type: ignore[override]
        redis_client = cast(Any, self)._get_redis("white")
        asyncio.create_task(redis_client.set(self.key, 1))
        super().set()

    def clear(self) -> None:
        # type: ignore[override]
        redis_client = cast(Any, self)._get_redis("white")
        asyncio.create_task(redis_client.delete(self.key))
        super().clear()

    async def wait(self) -> bool:
        # type: ignore[override]
        redis_client = await self._get_redis("read")
        while True:
            result = await redis_client.get(self.key)
            if result:
                break
            await asyncio.sleep(0.1)
        return await super().wait()

    def is_set(self) -> bool:
        # type: ignore[override]
        redis_client = cast(Any, self)._get_redis("read")
        result_coro = redis_client.get(self.key)
        result = asyncio.run(result_coro) # type: ignore
        return result is not None


async def set_token_rights(hash_token: int | str, timeout: int) -> None:
    await redis_master_client.set("token_rights:" + str(hash_token), "True", ex=timeout)


async def get_token_rights(hash_token: int | str) -> bytes | None:
    logger.debug("Получение прав на токен из Redis")
    answer = await redis_replica_client.get("token_rights:" + str(hash_token))
    return cast(bytes | None, answer)


async def set_check_last_24_hours(adv_original_id: int) -> None:
    await redis_master_client.set("check_adv_last_24_hours:" + str(adv_original_id), "True", ex=60 * 60 * 24)


async def check_last_24_hours(adv_original_id: int) -> bool:
    answer = await redis_replica_client.get("check_adv_last_24_hours:" + str(adv_original_id))
    return answer is not None


async def set_auto_block_statuses(new_statuses: List[Tuple[int, bool]]) -> None:
    data = {
        f"auto_block_status:{keywordsetting_original_id}": 1 if auto_block_status else 0
        for keywordsetting_original_id, auto_block_status in new_statuses
    }
    if data:
        await redis_master_client.mset(data)


async def set_auto_block_status(keywordsetting_original_id: int, auto_block_status: bool) -> None:
    key = "auto_block_status:" + str(keywordsetting_original_id)
    if auto_block_status is True:
        await redis_master_client.set(key, 1)
    else:
        await redis_master_client.set(key, 0)


async def get_auto_block_status(keywordsetting_original_id: int) -> bool:
    key = "auto_block_status:" + str(keywordsetting_original_id)
    answer = await redis_replica_client.get(key)
    if answer is None:
        return False
    else:
        answer = int(answer)
    auto_block_status = answer != 0
    return auto_block_status


async def set_user_cache_for_chat_id(user_chat_id: int, user_obj_as_json: str) -> None:
    await redis_master_client.set(f"user_data:{user_chat_id}", user_obj_as_json, ex=60 * 60 * 24)


async def get_user_cache_for_chat_id(user_chat_id: int) -> Dict[str, Any] | None:
    answer = await redis_replica_client.get(f"user_data:{user_chat_id}")
    if answer:
        return cast(Dict[str, Any], json.loads(answer))
    return None


async def set_target_positions_for_adv(adv_id: int, nmid: int, target_positions: List[int]) -> None:
    key = f"target_positions:{adv_id}:{nmid}"
    await redis_master_client.set(key, json.dumps(target_positions))


async def get_target_positions_for_adv(adv_id: int, nmid: int) -> List[int] | None:
    key = f"target_positions:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        return cast(List[int], json.loads(answer))
    return None


async def set_parsing_queue_data(data: Dict[str, Any], adv_type: str, item_id: int) -> None:
    key = f"parsing_queue_data:{adv_type}:{item_id}"
    await redis_master_client.set(key, json.dumps(data))


async def get_parsing_queue_data(adv_type: str, item_id: int) -> Dict[str, Any] | None:
    key = f"parsing_queue_data:{adv_type}:{item_id}"
    answer = await redis_replica_client.get(key)
    if answer:
        return cast(Dict[str, Any], json.loads(answer))
    return None


async def set_parsing_active(status: bool) -> None:
    await redis_master_client.set("parsing_active", "1" if status else "0")


async def get_parsing_active() -> bool:
    answer = await redis_replica_client.get("parsing_active")
    return answer == b"1"


async def add_dat_in_parsing_queue(adv_type: str, item_id: int, data: Dict[str, Any]) -> None:
    key = f"parsing_queue:{adv_type}:{item_id}"
    await cast(Any, redis_master_client).lpush(key, json.dumps(data)) # type: ignore


async def get_data_from_parsing_queue(adv_type: str, item_id: int) -> Dict[str, Any] | None:
    key = f"parsing_queue:{adv_type}:{item_id}"
    answer = await cast(Any, redis_master_client).rpop(key) # type: ignore
    if answer:
        return cast(Dict[str, Any], json.loads(answer))
    return None


async def set_adv_full_stat_cache(adv_id: int, full_adv_stat: FullAdvStat) -> None:
    key = f"adv_full_stat:{adv_id}"
    await redis_master_client.set(key, full_adv_stat.model_dump_json(), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_adv_full_stat_cache(adv_id: int) -> FullAdvStat | None:
    key = f"adv_full_stat:{adv_id}"
    answer = await redis_replica_client.get(key)
    if answer:
        return FullAdvStat.model_validate_json(answer) # type: ignore
    return None


async def set_adv_balances_cache(balances: Balances) -> None:
    key = "adv_balances"
    data = {
        "balance": balances.balance,
        "net": balances.net,
        "bonus": balances.bonus,
    }
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_SHORT_SEC) # type: ignore


async def get_adv_balances_cache() -> Balances | None:
    key = "adv_balances"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return Balances(data)
    return None


async def set_all_adv_settings_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_wb_item_positions(adv_id: int, nmid: int, positions: List[WBItemPosition]) -> None:
    key = f"wb_item_positions:{adv_id}:{nmid}"
    data = [pos.model_dump() for pos in positions]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_SHORT_SEC) # type: ignore


async def get_wb_item_positions(adv_id: int, nmid: int) -> List[WBItemPosition] | None:
    key = f"wb_item_positions:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [WBItemPosition(**pos_data) for pos_data in data]
    return None


async def add_calculated_keyword(calculated_keyword: CalculatedKeyword) -> None:
    key = f"calculated_keyword:{calculated_keyword.keyword_id}:{calculated_keyword.position}"
    await redis_master_client.set(key, calculated_keyword.model_dump_json(), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_calculated_keyword(keyword_id: int, position: int) -> CalculatedKeyword | None:
    key = f"calculated_keyword:{keyword_id}:{position}"
    answer = await redis_replica_client.get(key)
    if answer:
        return CalculatedKeyword.model_validate_json(answer) # type: ignore
    return None


async def set_min_cpm_adv_data_cache(min_cpm_data: Dict[str, Any]) -> None:
    key = "min_cpm_adv_data"
    await redis_master_client.set(key, json.dumps(min_cpm_data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_min_cpm_adv_data_cache() -> Dict[str, Any] | None:
    key = "min_cpm_adv_data"
    answer = await redis_replica_client.get(key)
    if answer:
        return cast(Dict[str, Any], json.loads(answer))
    return None


async def get_all_active_adv_settings_cache() -> List[AdvSetting] | None:
    key = "all_active_adv_settings"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_active_adv_settings_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_active_adv_settings"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_active_adv_settings_for_parsing_cache() -> List[AdvSetting] | None:
    key = "all_active_adv_settings_for_parsing"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_active_adv_settings_for_parsing_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_active_adv_settings_for_parsing"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_active_adv_settings_for_bidder_cache() -> List[AdvSetting] | None:
    key = "all_active_adv_settings_for_bidder"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_active_adv_settings_for_bidder_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_active_adv_settings_for_bidder"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_active_adv_settings_for_white_list_updater_cache() -> List[AdvSetting] | None:
    key = "all_active_adv_settings_for_white_list_updater"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_active_adv_settings_for_white_list_updater_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_active_adv_settings_for_white_list_updater"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_active_adv_settings_for_target_place_updater_cache() -> List[AdvSetting] | None:
    key = "all_active_adv_settings_for_target_place_updater"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_active_adv_settings_for_target_place_updater_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_active_adv_settings_for_target_place_updater"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_sales_plan_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_sales_plan"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_sales_plan_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_sales_plan"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_target_price_for_order_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_target_price_for_order"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_target_price_for_order_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_target_price_for_order"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_max_price_for_order_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_max_price_for_order"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_max_price_for_order_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_max_price_for_order"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_cpm_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_cpm"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_cpm_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_cpm"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_bidder_for_auto_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_bidder_for_auto"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_bidder_for_auto_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_bidder_for_auto"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_add_only_relevant_phrase_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_add_only_relevant_phrase"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_add_only_relevant_phrase_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_add_only_relevant_phrase"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_add_new_key_from_search_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_add_new_key_from_search"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_add_new_key_from_search_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_add_new_key_from_search"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_minus_bad_key_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_minus_bad_key"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_minus_bad_key_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_minus_bad_key"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_stop_bad_adv_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_stop_bad_adv"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_stop_bad_adv_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_stop_bad_adv"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_restart_adv_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_restart_adv"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_restart_adv_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_restart_adv"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_set_status_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_set_status"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_set_status_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_set_status"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_update_target_place_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_update_target_place"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_update_target_place_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_update_target_place"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_add_new_key_from_ads_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_add_new_key_from_ads"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_add_new_key_from_ads_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_add_new_key_from_ads"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_minus_bad_key_from_ads_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_minus_bad_key_from_ads"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_minus_bad_key_from_ads_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_minus_bad_key_from_ads"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_update_keyword_stat_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_update_keyword_stat"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_update_keyword_stat_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_update_keyword_stat"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_set_bid_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_set_bid"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_set_bid_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_set_bid"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_update_price_on_ad_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_update_price_on_ad"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_update_price_on_ad_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_update_price_on_ad"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_adv_full_stat_for_today_cache(adv_id: int) -> FullAdvStat | None:
    key = f"adv_full_stat_for_today:{adv_id}"
    answer = await redis_replica_client.get(key)
    if answer:
        return FullAdvStat.model_validate_json(answer) # type: ignore
    return None


async def set_adv_full_stat_for_today_cache(adv_id: int, full_adv_stat: FullAdvStat) -> None:
    key = f"adv_full_stat_for_today:{adv_id}"
    await redis_master_client.set(key, full_adv_stat.model_dump_json(), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_change_price_for_order_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_change_price_for_order"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_change_price_for_order_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_change_price_for_order"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_change_plan_for_day_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_change_plan_for_day"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_change_plan_for_day_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_change_plan_for_day"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_change_target_place_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_change_target_place"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_change_target_place_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_change_target_place"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_restart_adv_when_need_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_restart_adv_when_need"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_restart_adv_when_need_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_restart_adv_when_need"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_all_adv_settings_for_auto_stop_bad_adv_when_need_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_auto_stop_bad_adv_when_need"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_auto_stop_bad_adv_when_need_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_auto_stop_bad_adv_when_need"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def set_adv_target_place_for_today_cache(adv_id: int, nmid: int, target_place: int) -> None:
    key = f"adv_target_place_for_today:{adv_id}:{nmid}"
    await redis_master_client.set(key, str(target_place), ex=settings.REDIS_CACHE_TIME_SHORT_SEC) # type: ignore


async def get_adv_target_place_for_today_cache(adv_id: int, nmid: int) -> int | None:
    key = f"adv_target_place_for_today:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        return int(answer)
    return None


async def get_all_adv_settings_for_sales_plan_for_day_cache() -> List[AdvSetting] | None:
    key = "all_adv_settings_for_sales_plan_for_day"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [AdvSetting(**adv_data) for adv_data in data]
    return None


async def set_all_adv_settings_for_sales_plan_for_day_cache(adv_settings: List[AdvSetting]) -> None:
    key = "all_adv_settings_for_sales_plan_for_day"
    data = [adv.model_dump() for adv in adv_settings]
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_wb_token_cache(token: str) -> str | None:
    key = f"wb_token:{token}"
    answer = await redis_replica_client.get(key)
    if answer:
        return cast(str, answer.decode())
    return None


async def set_wb_token_cache(token: str, wb_token_data: str) -> None:
    key = f"wb_token:{token}"
    await redis_master_client.set(key, wb_token_data, ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_auto_update_target_place_task_id_cache(adv_id: int, nmid: int) -> str | None:
    key = f"auto_update_target_place_task_id:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        return cast(str, answer.decode())
    return None


async def set_auto_update_target_place_task_id_cache(adv_id: int, nmid: int, task_id: str) -> None:
    key = f"auto_update_target_place_task_id:{adv_id}:{nmid}"
    await redis_master_client.set(key, task_id, ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def delete_auto_update_target_place_task_id_cache(adv_id: int, nmid: int) -> None:
    key = f"auto_update_target_place_task_id:{adv_id}:{nmid}"
    await redis_master_client.delete(key)


async def get_auto_update_keyword_stat_task_id_cache(adv_id: int, nmid: int) -> str | None:
    key = f"auto_update_keyword_stat_task_id:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        return cast(str, answer.decode())
    return None


async def set_auto_update_keyword_stat_task_id_cache(adv_id: int, nmid: int, task_id: str) -> None:
    key = f"auto_update_keyword_stat_task_id:{adv_id}:{nmid}"
    await redis_master_client.set(key, task_id, ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def delete_auto_update_keyword_stat_task_id_cache(adv_id: int, nmid: int) -> None:
    key = f"auto_update_keyword_stat_task_id:{adv_id}:{nmid}"
    await redis_master_client.delete(key)


async def get_bidder_for_auto_task_id_cache(adv_id: int, nmid: int) -> str | None:
    key = f"bidder_for_auto_task_id:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        return cast(str, answer.decode())
    return None


async def set_bidder_for_auto_task_id_cache(adv_id: int, nmid: int, task_id: str) -> None:
    key = f"bidder_for_auto_task_id:{adv_id}:{nmid}"
    await redis_master_client.set(key, task_id, ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def delete_bidder_for_auto_task_id_cache(adv_id: int, nmid: int) -> None:
    key = f"bidder_for_auto_task_id:{adv_id}:{nmid}"
    await redis_master_client.delete(key)


async def get_auto_update_white_list_task_id_cache(adv_id: int, nmid: int) -> str | None:
    key = f"auto_update_white_list_task_id:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        return cast(str, answer.decode())
    return None


async def set_auto_update_white_list_task_id_cache(adv_id: int, nmid: int, task_id: str) -> None:
    key = f"auto_update_white_list_task_id:{adv_id}:{nmid}"
    await redis_master_client.set(key, task_id, ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def delete_auto_update_white_list_task_id_cache(adv_id: int, nmid: int) -> None:
    key = f"auto_update_white_list_task_id:{adv_id}:{nmid}"
    await redis_master_client.delete(key)


async def get_adv_full_stat_for_dates_cache(adv_id: int, start_date: datetime.date, end_date: datetime.date) -> FullAdvStat | None:
    key = f"adv_full_stat_for_dates:{adv_id}:{start_date.isoformat()}:{end_date.isoformat()}"
    answer = await redis_replica_client.get(key)
    if answer:
        return FullAdvStat.model_validate_json(answer) # type: ignore
    return None


async def set_adv_full_stat_for_dates_cache(adv_id: int, start_date: datetime.date, end_date: datetime.date, full_adv_stat: FullAdvStat) -> None:
    key = f"adv_full_stat_for_dates:{adv_id}:{start_date.isoformat()}:{end_date.isoformat()}"
    await redis_master_client.set(key, full_adv_stat.model_dump_json(), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def get_adv_full_stats_for_dates_by_adv_ids_cache(adv_ids_str: str, start_date: datetime.date, end_date: datetime.date) -> List[FullAdvStat] | None:
    key = f"adv_full_stats_for_dates_by_adv_ids:{adv_ids_str}:{start_date.isoformat()}:{end_date.isoformat()}"
    answer = await redis_replica_client.get(key)
    if answer:
        data = json.loads(answer)
        return [FullAdvStat.model_validate_json(item) for item in data] # type: ignore
    return None


async def set_adv_full_stats_for_dates_by_adv_ids_cache(adv_ids_str: str, start_date: datetime.date, end_date: datetime.date, full_adv_stats: List[FullAdvStat]) -> None:
    key = f"adv_full_stats_for_dates_by_adv_ids:{adv_ids_str}:{start_date.isoformat()}:{end_date.isoformat()}"
    data = [item.model_dump() for item in full_adv_stats] # type: ignore
    await redis_master_client.set(key, json.dumps(data), ex=settings.REDIS_CACHE_TIME_LONG_SEC) # type: ignore


async def set_adv_target_place_for_day_cache(adv_id: int, nmid: int, date: datetime.date, target_place: int) -> None:
    key = f"adv_target_place_for_day:{adv_id}:{nmid}:{date.isoformat()}"
    await redis_master_client.set(key, str(target_place), ex=settings.REDIS_CACHE_TIME_SHORT_SEC) # type: ignore


async def get_last_set_up_target_place_cache(adv_id: int, nmid: int) -> int | None:
    key = f"last_set_up_target_place:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        return int(answer)
    return None


async def set_last_set_up_target_place_cache(adv_id: int, nmid: int, target_place: int) -> None:
    key = f"last_set_up_target_place:{adv_id}:{nmid}"
    await redis_master_client.set(key, str(target_place), ex=settings.REDIS_CACHE_TIME_SHORT_SEC) # type: ignore


async def get_last_set_down_target_place_cache(adv_id: int, nmid: int) -> int | None:
    key = f"last_set_down_target_place:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        return int(answer)
    return None


async def set_last_set_down_target_place_cache(adv_id: int, nmid: int, target_place: int) -> None:
    key = f"last_set_down_target_place:{adv_id}:{nmid}"
    await redis_master_client.set(key, str(target_place), ex=settings.REDIS_CACHE_TIME_SHORT_SEC) # type: ignore


async def get_last_target_place_update_time_cache(adv_id: int, nmid: int) -> datetime.datetime | None:
    key = f"last_target_place_update_time:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        return datetime.datetime.fromisoformat(answer.decode())
    return None


async def set_last_target_place_update_time_cache(adv_id: int, nmid: int, update_time: datetime.datetime) -> None:
    key = f"last_target_place_update_time:{adv_id}:{nmid}"
    await redis_master_client.set(key, update_time.isoformat(), ex=settings.REDIS_CACHE_TIME_SHORT_SEC) # type: ignore


async def get_last_keyword_stat_update_time_cache(adv_id: int, nmid: int) -> datetime.datetime | None:
    key = f"last_keyword_stat_update_time:{adv_id}:{nmid}"
    answer = await redis_replica_client.get(key)
    if answer:
        return datetime.datetime.fromisoformat(answer.decode())
    return None


async def set_last_keyword_stat_update_time_cache(adv_id: int, nmid: int, update_time: datetime.datetime) -> None:
    key = f"last_keyword_stat_update_time:{adv_id}:{nmid}"
    await redis_master_client.set(key, update_time.isoformat(), ex=settings.REDIS_CACHE_TIME_SHORT_SEC) # type: ignore
