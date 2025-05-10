from app.core.redis_manager.base_redis_manager import BaseRedis


class RedisManager(BaseRedis):

    def get_key(self, auto_adv_id) -> str:
        return f"last_spend:{auto_adv_id}"

    async def get_last_spend_sum(self, auto_adv_id: int) -> float | None:
        key = self.get_key(auto_adv_id)
        value = await self.client.get(key)
        return float(value.decode()) if value else None

    async def set_last_spend_sum(self, auto_adv_id: int, sum_spend_now: float):
        key = self.get_key(auto_adv_id)
        await self.client.set(key, sum_spend_now)
