import datetime
import json

from app.core.redis_manager.base_redis_manager import BaseRedis
from app.modules.common_slaves.wildberries.models import AdvSetting


class LastTargetPlaceUpdateRedisManager(BaseRedis):

    @staticmethod
    def get_key(adv: AdvSetting) -> str:
        return f"last_target_place_update:{adv.adv_id}"

    async def get_last_target_place_update(
        self, adv: AdvSetting
    ) -> tuple[datetime.datetime, float] | None:
        """
        Получает дату последнего обновления таргет плейс и сумму расхода по ключевым словам на тот момент.
        """
        key = self.get_key(adv)
        value = await self.client.get(key)
        if not value:
            # Возвращаем значение по умолчанию
            return None
        try:
            data = json.loads(value)
            timestamp = datetime.datetime.fromisoformat(data["timestamp"])
            spend = float(data["spend"])
            return timestamp, spend
        except (KeyError, ValueError, TypeError) as e:
            # В случае некорректных данных — возвращаем дефолт
            return datetime.datetime.min, 0.0

    async def set_last_target_place_update(
        self,
        adv: AdvSetting,
        timestamp: datetime.datetime,
        spend_sum_from_keywords_now: float,
    ):
        """
        Устанавливает новую дату обновления и сумму расхода.
        """
        data = {
            "timestamp": timestamp.isoformat(),
            "spend": spend_sum_from_keywords_now,
        }
        key = self.get_key(adv)
        await self.client.set(key, json.dumps(data))
