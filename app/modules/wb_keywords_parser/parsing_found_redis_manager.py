from time import time

from app.core.redis_manager.base_redis_manager import BaseRedis


class ParsingFoundRedisManager(BaseRedis):
    async def add_last_found_page_for_text_nmid(
        self, text: str, nmid: int, page: int
    ) -> None:
        key = f"found_pages:{text}:{nmid}"
        score: float = float(time())
        await self._client.zadd(key, {str(page): score})

    async def add_last_not_found_page_for_text_nmid(self, text: str, nmid: int, page: int) -> None:
        key = f"not_found_pages:{text}:{nmid}"
        score: float = float(time())
        await self._client.zadd(key, {str(page): score})

    async def get_found_pages_for_text_nmid(self, text: str, nmid: int) -> list[int]:
        key = f"found_pages:{text}:{nmid}"
        pages = await self._client.zrevrange(key, 0, -1)
        return [int(page) for page in pages]

    async def get_not_found_pages_for_text_nmid(
        self, text: str, nmid: int
    ) -> list[int]:
        key = f"not_found_pages:{text}:{nmid}"
        pages = await self._client.zrevrange(key, 0, -1)
        return [int(page) for page in pages]
