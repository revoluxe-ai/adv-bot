from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.modules.common_slaves.wildberries.models import AdvSetting


class MaxCpmRedisStatusManager(BaseRedisManager):
    prefix = "auto_max_cpm"

    def _get_key(self, adv_setting: AdvSetting) -> str:
        return f"{self.prefix}:{adv_setting.adv_id}"

    async def set(self, adv_setting: AdvSetting, max_cpm: int) -> None:
        key = self._get_key(adv_setting)
        await self._client.set(key, str(max_cpm))

    async def get(self, adv_setting: AdvSetting) -> int | None:
        key = self._get_key(adv_setting)
        value = await self._client.get(key)
        if value is not None:
            return int(value)
        return None
