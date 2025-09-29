import json
import logging
import os
from typing import Iterable, List, Tuple

import redis.asyncio as redis

from shared_lib.settings_master import settings
from .adc_manager import AbcManager
from . import text_cleaner

logger = logging.getLogger(__name__)
logger.debug("data_getter module imported")

_redis_read = None
_redis_write = None
_fake_mode = os.getenv("PREDICT_CTR_FAKE_FEATURES", "0").lower() in {"1", "true", "yes", "on"}
_fake_item_vector = [0.1 * i for i in range(16)]
_fake_keyword_vector = [0.05 * i for i in range(32)]


def _init_clients():
    global _redis_read, _redis_write
    if _fake_mode:
        logger.info("DataGetter: FAKE FEATURES MODE включен (PREDICT_CTR_FAKE_FEATURES=1)")
        return
    if _redis_read and _redis_write:
        return
    logger.debug("_init_clients(): initializing redis clients")
    try:
        replica_host = settings.REDIS_REPLICA_HOST
    except Exception:
        replica_host = "localhost"
    try:
        master_host = settings.REDIS_MASTER_HOST
    except Exception:
        master_host = replica_host or "localhost"
    try:
        port = settings.REDIS_PORT
    except Exception:
        port = 6379
    _redis_read = redis.StrictRedis(host=replica_host or "localhost", port=port, db=0)
    _redis_write = redis.StrictRedis(host=master_host or "localhost", port=port, db=0)
    logger.info(f"Redis clients initialized (master={master_host}, replica={replica_host}, port={port})")


class DataGetter(AbcManager):
    """Минимальный поставщик фич для модели.

    Предполагаемый формат ключей в Redis:
      item_vector:{nmid} -> JSON list[float]
      keyword_vector:{clean_keyword} -> JSON list[float]
    """

    @staticmethod
    async def get_item_features_from_redis(nmids_batch: Iterable[int]) -> List[Tuple[int, list[float]]]:
        logger.debug("DataGetter.get_item_features_from_redis() nmids_batch=%s", list(nmids_batch))
        nmids_batch = list(nmids_batch)
        _init_clients()
        if _fake_mode:
            result_fake = [(int(nmid), _fake_item_vector) for nmid in nmids_batch]
            logger.debug("FAKE MODE: return %d item feature vectors", len(result_fake))
            return result_fake
        result: List[Tuple[int, list[float]]] = []
        for nmid in nmids_batch:
            key = f"item_vector:{nmid}"
            try:
                data = await _redis_read.get(key)  # type: ignore[attr-defined]
            except Exception:
                logger.error("Ошибка чтения item_vector из Redis (nmid=%s)", nmid, exc_info=True)
                continue
            if not data:
                logger.debug("item_vector not found nmid=%s", nmid)
                continue
            try:
                vector = json.loads(data.decode("utf-8"))
                if isinstance(vector, list):
                    result.append((int(nmid), vector))
            except Exception:
                logger.warning("Некорректный JSON item_vector для %s", nmid)
        logger.debug("DataGetter.get_item_features_from_redis() -> %d", len(result))
        return result

    @staticmethod
    async def get_keyword_features_from_redis(keywords: Iterable[str]) -> List[Tuple[str, list[float]]]:
        keywords = list(keywords)
        logger.debug("DataGetter.get_keyword_features_from_redis() keywords=%s", keywords)
        _init_clients()
        if _fake_mode:
            result_fake = [(kw, _fake_keyword_vector) for kw in keywords]
            logger.debug("FAKE MODE: return %d keyword feature vectors", len(result_fake))
            return result_fake
        result: List[Tuple[str, list[float]]] = []
        for kw in keywords:
            clean_kw = text_cleaner.clear(kw)
            key = f"keyword_vector:{clean_kw}"
            try:
                data = await _redis_read.get(key)  # type: ignore[attr-defined]
            except Exception:
                logger.error("Ошибка чтения keyword_vector из Redis (kw=%s)", kw, exc_info=True)
                continue
            if not data:
                logger.debug("keyword_vector not found kw=%s", kw)
                continue
            try:
                vector = json.loads(data.decode("utf-8"))
                if isinstance(vector, list):
                    result.append((kw, vector))
            except Exception:
                logger.warning("Некорректный JSON keyword_vector для %s", kw)
        logger.debug("DataGetter.get_keyword_features_from_redis() -> %d", len(result))
        return result
