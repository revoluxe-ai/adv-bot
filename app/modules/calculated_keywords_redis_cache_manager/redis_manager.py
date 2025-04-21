from app.core.redis_manager import RedisManager
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword


class RedisCalculatedKeywordsCacheManager(RedisManager):

    async def set_calculated_keywords(self, keywords: list[CalculatedKeyword], adv_id: int) -> None:
        """
        Сохранение списка ключевых слов в Redis.
        """
        async with self.client.pipeline() as pipe:
            for keyword in keywords:
                await pipe.hset(
                    name=f"calculated_keywords:{adv_id}",
                    key=keyword.text,
                    value=keyword.to_json()
                )

    async def get_calculated_keywords(self, keywords: list[CalculatedKeyword]) -> list[CalculatedKeyword]:
        """
        Получение списка ключевых слов из Redis.
        """
        async with self.client.pipeline() as pipe:
            for keyword in keywords:
                await pipe.hget(
                    name=f"calculated_keywords:{keyword.adv_id}",
                    key=keyword.text
                )
            results = await pipe.execute()

        return [CalculatedKeyword.from_dict(result) for result in results if result is not None]

    async def get_calculated_keyword(self, adv_id: int, keyword: str) -> CalculatedKeyword | None:
        """
        Получение одного ключевого слова из Redis.
        """
        result = await self.client.hget(
            name=f"calculated_keywords:{adv_id}",
            key=keyword
        )
        if result is not None:
            return CalculatedKeyword.from_dict(result)
        return None
