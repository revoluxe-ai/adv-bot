import json

from app.core.redis_manager_v2.redis_client import RedisClient as BaseRedisManager


class RedisManager(BaseRedisManager):
    async def update_keywords_vectors(
        self, keywords_vectors: dict[str, list[float]]
    ) -> None:
        pipe = self.write_pipeline()
        for keyword, vector in keywords_vectors.items():
            key = f"keyword_vector:{keyword}"
            pipe.set(key, json.dumps(vector))
        await pipe.execute()

    async def update_items_vectors(self, items_vectors: dict[int, list[float]]) -> None:
        pipe = self.write_pipeline()
        for nmid, vector in items_vectors.items():
            key = f"item_vector:{nmid}"
            pipe.set(key, json.dumps(vector))
        await pipe.execute()
