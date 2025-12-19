import datetime

from app.core.redis_manager.base_redis_manager import BaseRedis
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.timezone import ensure_moscow, now_moscow

__all__ = ["MainRedisManager"]


class LastSpendSumRedisManager(BaseRedis):
    @staticmethod
    def _get_key(adv: AdvSetting) -> str:
        auto_adv_id = adv.adv_id
        return f"last_spend:{auto_adv_id}"

    async def get_last_spend_sum(self, adv: AdvSetting) -> float | None:
        key = self._get_key(adv)
        value = await self.client.get(key)
        return float(value.decode()) if value else None

    async def set_last_spend_sum(self, adv: AdvSetting, sum_spend_now: float) -> None:
        key = self._get_key(adv)
        await self.client.set(key, sum_spend_now)


class LastDateTimeDeleteWhiteListRedisManager(BaseRedis):
    @staticmethod
    def _get_key(adv: AdvSetting) -> str:
        adv_id = adv.adv_id
        return f"last_delete_phrase_from_white_list:{adv_id}"

    async def get_last_delete_datetime(
        self, adv: AdvSetting
    ) -> datetime.datetime | None:
        key = self._get_key(adv)
        value = await self.client.get(key)
        if value:
            # Assuming the datetime is stored in ISO format
            return ensure_moscow(datetime.datetime.fromisoformat(value.decode()))
        return None

    async def set_last_delete_datetime(self, adv: AdvSetting) -> None:
        now = now_moscow()
        key = self._get_key(adv)
        # Store datetime in ISO format
        await self.client.set(key, now.isoformat())


class LastAddingToWhiteListRedisData(BaseRedis):
    @staticmethod
    def _get_key(adv: AdvSetting) -> str:
        return f"white_list:add:{adv.adv_id}"

    async def get_last_adding_to_white_list(
        self, adv: AdvSetting
    ) -> datetime.datetime | None:
        key = self._get_key(adv)
        value = await self.client.get(key)
        if not value:
            return None
        try:
            date = ensure_moscow(datetime.datetime.fromisoformat(value))
        except ValueError:
            return None
        return date

    async def set_last_adding_to_white_list(
        self,
        adv: AdvSetting,
        data_adding_add_datetime: datetime.datetime,
    ) -> None:
        key = self._get_key(adv)
        value = f"{data_adding_add_datetime.isoformat()}"
        await self.client.set(key, value)


class MainRedisManager:
    delete_last_datetime = LastDateTimeDeleteWhiteListRedisManager()
    adding_key_data = LastAddingToWhiteListRedisData()
