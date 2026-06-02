import json
import logging
from collections.abc import Awaitable

from pydantic import ValidationError

from app.core.redis_manager import RedisManager
from app.snapshot_data_updater.config import calculated_keywords_hash_ttl_sec

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

logger = logging.getLogger(__name__)

# Поле-маркер: hash существует, keywords после warmup/расчёта — пустой список.
_CALCULATED_KEYWORDS_EMPTY_FIELD = "__empty__"


def _field_name(raw: str | bytes) -> str:
    if isinstance(raw, bytes):
        return raw.decode()
    return raw


class RedisCalculatedKeywordsCacheManager(RedisManager):
    async def set_calculated_keywords(
        self, keywords: list[CalculatedKeyword], adv_id: int
    ) -> None:
        """Сохранение списка keywords в Redis hash ``calculated_keywords:{adv_id}``.

        После записи — ``EXPIRE`` (``CALCULATED_KEYWORDS_REDIS_TTL_SEC`` или
        ``4 × SNAPSHOT_KEYWORDS_STALE_SEC``). Истёкший hash → cache miss в shop-runner.
        """
        logger.debug(f"Setting keywords for adv_id {adv_id}, count: {len(keywords)}")
        key = f"calculated_keywords:{adv_id}"
        ttl_sec = calculated_keywords_hash_ttl_sec()
        if not keywords:
            async with self.client.pipeline() as pipe:
                pipe.delete(key)
                pipe.hset(name=key, key=_CALCULATED_KEYWORDS_EMPTY_FIELD, value="1")
                pipe.expire(key, ttl_sec)
                await pipe.execute()
            return
        async with self.client.pipeline() as pipe:
            for keyword in keywords:
                logger.debug(f"Setting key: {key}, keyword: {keyword.text}")
                pipe.hset(name=key, key=keyword.text, value=keyword.model_dump_json())
            pipe.expire(key, ttl_sec)
            await pipe.execute()

    async def get_calculated_keyword(
        self, adv_id: int, keyword: str
    ) -> CalculatedKeyword:
        """
        Получение одного ключевого слова из Redis.
        """
        # TODO: Возвращает байты, переделать на новый редис-клиент
        key = f"calculated_keywords:{adv_id}"
        logger.debug(f"Getting keyword from key: {key}, keyword: {keyword}")
        result_coro: Awaitable[bytes] = self.client.hget(name=key, key=keyword)
        if isinstance(result_coro, Awaitable):
            result = await result_coro
        else:
            result = result_coro
        result_str = result.decode()
        #TODO: Добавить сюда фоллбек с возвратом на список ключей для перезагрузки списка ключей в кеш
        return CalculatedKeyword.model_validate(json.loads(result_str))

    async def get_calculated_keywords(
        self, keywords: list[CalculatedKeyword]
    ) -> list[CalculatedKeyword]:
        """
        Получение списка ключевых слов из Redis.
        """
        logger.info(f"Getting keywords, count: {len(keywords)}")
        async with self.client.pipeline() as pipe:
            for keyword in keywords:
                key = f"calculated_keywords:{keyword.adv_id}"
                logger.debug(
                    f"Getting keyword from key: {key}, keyword: {keyword.text}"
                )
                pipe.hget(name=key, key=keyword.text)
            results = await pipe.execute()

        return [
            CalculatedKeyword.model_validate(result)
            for result in results
            if result is not None
        ]

    async def get_calculated_keywords_map(
        self, adv_id: int, texts: list[str]
    ) -> dict[str, CalculatedKeyword]:
        """
        Batch get calculated keywords from Redis by adv_id and text list.
        Returns dict text -> CalculatedKeyword for texts that exist in cache.
        """
        if not texts:
            return {}
        key = f"calculated_keywords:{adv_id}"
        async with self.client.pipeline() as pipe:
            for text in texts:
                pipe.hget(name=key, key=text)
            results = await pipe.execute()
        out: dict[str, CalculatedKeyword] = {}
        for text, raw in zip(texts, results):
            if raw is None:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode()
            try:
                out[text] = CalculatedKeyword.model_validate(json.loads(raw))
            except (json.JSONDecodeError, Exception):  # noqa: BLE001
                continue
        return out

    async def get_all_calculated_keywords_for_adv(
        self, adv_id: int
    ) -> list[CalculatedKeyword] | None:
        """Все keywords из hash ``calculated_keywords:{adv_id}``.

        Returns:
            ``None`` — ключ отсутствует, истёк TTL или нет маркера ``__empty__``.
            ``[]`` — hash с маркером ``__empty__`` (легитимный пустой warmup).
            иначе список ``CalculatedKeyword``.
        """
        key = f"calculated_keywords:{adv_id}"
        raw_map = await self.client.hgetall(key)
        if not raw_map:
            return None
        out: list[CalculatedKeyword] = []
        has_empty_marker = False
        for field, raw in raw_map.items():
            if _field_name(field) == _CALCULATED_KEYWORDS_EMPTY_FIELD:
                has_empty_marker = True
                continue
            if isinstance(raw, bytes):
                raw = raw.decode()
            try:
                out.append(CalculatedKeyword.model_validate(json.loads(raw)))
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
                continue
        if out:
            return out
        if has_empty_marker:
            return []
        return None
