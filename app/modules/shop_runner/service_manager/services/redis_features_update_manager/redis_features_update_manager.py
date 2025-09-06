from app.modules.common_slaves.wildberries.models import KeywordSetting, AdvSetting
from .neo4j_manager.neo4j_manager import Neo4jManager
from .redis_manager.redis_item_features_manager import RedisManager
from typing import  Awaitable
class RedisFeaturesUpdateManager:

    def __init__(self):
        self._neo4j_manager = Neo4jManager()
        self._redis_manager = RedisManager()

    async def update_keyword_features(self, keywords_coro: Awaitable[list[KeywordSetting]]) -> None:
        keywords = await keywords_coro
        texts = [keyword.text for keyword in keywords]
        keywords_vectors: dict[str, list[float]] = (
            await self._neo4j_manager.get_keywords_vectors(texts)
        )
        await self._redis_manager.update_keywords_vectors(keywords_vectors)

    async def update_items_features(self, adv: AdvSetting) -> None:
        nmids = set(adv.nmids)
        items_vectors: dict[int, list[float]] = (
            await self._neo4j_manager.get_items_vectors(nmids)
        )
        await self._redis_manager.update_items_vectors(items_vectors)
