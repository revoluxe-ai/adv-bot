import logging
from collections.abc import Awaitable

from app.core.redis_manager import RedisManager
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword

logger = logging.getLogger(__name__)


class RedisCalculatedKeywordsCacheManager(RedisManager):
    async def set_calculated_keywords(self, keywords: list[CalculatedKeyword], adv_id: int) -> None:
        """
        Сохранение списка ключевых слов в Redis.
        """
        logger.info(f"Setting keywords for adv_id {adv_id}, count: {len(keywords)}")
        if not keywords:
            return
        async with self.client.pipeline() as pipe:
            for keyword in keywords:
                key = f"calculated_keywords:{adv_id}"
                logger.debug(f"Setting key: {key}, keyword: {keyword.text}")
                pipe.hset(name=key, key=keyword.text, value=keyword.to_json())
            await pipe.execute()

    async def get_calculated_keyword(self, adv_id: int, keyword: str) -> CalculatedKeyword | None:
        """
        Получение одного ключевого слова из Redis.
        """
        key = f"calculated_keywords:{adv_id}"
        logger.debug(f"Getting keyword from key: {key}, keyword: {keyword}")
        result = self.client.hget(name=key, key=keyword)
        if isinstance(result, Awaitable):
            result = await result
        return CalculatedKeyword.from_json(result) if result is not None else None

    async def get_calculated_keywords(self, keywords: list[CalculatedKeyword]) -> list[CalculatedKeyword]:
        """
        Получение списка ключевых слов из Redis.
        """
        logger.info(f"Getting keywords, count: {len(keywords)}")
        async with self.client.pipeline() as pipe:
            for keyword in keywords:
                key = f"calculated_keywords:{keyword.adv_id}"
                logger.debug(f"Getting keyword from key: {key}, keyword: {keyword.text}")
                pipe.hget(name=key, key=keyword.text)
            results = await pipe.execute()

        return [CalculatedKeyword.from_json(result) for result in results if result is not None]
