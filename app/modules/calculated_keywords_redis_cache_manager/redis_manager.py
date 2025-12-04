import json
import logging
from collections.abc import Awaitable

from app.core.redis_manager import RedisManager

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

logger = logging.getLogger(__name__)


class RedisCalculatedKeywordsCacheManager(RedisManager):
    async def set_calculated_keywords(
        self, keywords: list[CalculatedKeyword], adv_id: int
    ) -> None:
        """
        Сохранение списка ключевых слов в Redis.
        """
        logger.debug(f"Setting keywords for adv_id {adv_id}, count: {len(keywords)}")
        if not keywords:
            return
        async with self.client.pipeline() as pipe:
            for keyword in keywords:
                key = f"calculated_keywords:{adv_id}"
                logger.debug(f"Setting key: {key}, keyword: {keyword.text}")
                pipe.hset(name=key, key=keyword.text, value=keyword.model_dump_json())
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
