import datetime

from app.core.redis_manager.base_redis_manager import BaseRedis
from app.modules.common_slaves.wildberries.models import AdvSetting

__all__ = ["MainRedisManager"]


class LastSpendSumForDeletingWhiteListRedisManager(BaseRedis):

    @staticmethod
    def _get_key(auto_adv_id: int) -> str:
        return f"last_spend:{auto_adv_id}"

    async def get_last_spend_sum(self, auto_adv_id: int) -> float | None:
        key = self._get_key(auto_adv_id)
        value = await self.client.get(key)
        return float(value.decode()) if value else None

    async def set_last_spend_sum(self, auto_adv_id: int, sum_spend_now: float) -> None:
        key = self._get_key(auto_adv_id)
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
            return datetime.datetime.fromisoformat(value.decode())
        return None

    async def set_last_delete_datetime(self, adv: AdvSetting) -> None:
        now = datetime.datetime.now()
        key = self._get_key(adv)
        # Store datetime in ISO format
        await self.client.set(key, now.isoformat())


class LastAddingToWhiteListRedisData(BaseRedis):

    @staticmethod
    def _get_key(adv: AdvSetting) -> str:
        return f"white_list:add:{adv.adv_id}"

    async def get_last_adding_to_white_list(
        self, adv: AdvSetting
    ) -> tuple[datetime.datetime, int] | None:
        key = self._get_key(adv)
        value = await self.client.get(key)
        if not value:
            return None
        date_str, views_str = value.decode().split("|")
        date = datetime.datetime.fromisoformat(date_str)
        views = int(views_str)
        return date, views

    async def set_last_adding_to_white_list(
        self,
        adv: AdvSetting,
        data_adding_add_datetime: datetime.datetime,
        sum_views_from_keyword: int,
    ) -> None:
        key = self._get_key(adv)
        value = f"{data_adding_add_datetime.isoformat()}|{sum_views_from_keyword}"
        await self.client.set(key, value)


class MainRedisManager:
    delete_key_data = LastSpendSumForDeletingWhiteListRedisManager()
    delete_last_datetime = LastDateTimeDeleteWhiteListRedisManager()
    adding_key_data = LastAddingToWhiteListRedisData()
