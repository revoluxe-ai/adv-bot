import json
from datetime import datetime

from app.core.redis_manager.base_redis_manager import BaseRedis


class AdvActiveKeywordUpdateStateManager(BaseRedis):
    time_str_format = "%d-%m-%Y %H:%M:%S"
    invalid_norm_query_ttl_seconds = 60 * 60 * 24

    @staticmethod
    def _get_key(adv_id: int) -> str:
        """
        Формирует ключ для хранения данных в Redis.
        """
        return f"minus_update:{adv_id}"

    @staticmethod
    def _get_invalid_norm_queries_key(adv_id: int, nmid: int) -> str:
        return f"minus_invalid_norm_queries:{adv_id}:{nmid}"

    async def set_one(self, adv_id: int) -> None:
        """
        Сохраняет метку времени обновления в Redis.

        :param adv_id: ID рекламы.
        :param update_time_stamp: Момент времени обновления.
        """
        key = self._get_key(adv_id)
        update_time_stamp = datetime.now()
        datetime_str = update_time_stamp.strftime(
            self.time_str_format
        )  # Преобразование в строку
        await self._client.set(key, datetime_str)  # Асинхронная установка значения

    async def get_one(self, adv_id: int) -> datetime | None:
        """
        Получает метку времени обновления из Redis.

        :param adv_id: ID рекламы.
        :return: Момент времени обновления.
        """
        key = self._get_key(adv_id)
        datetime_bytes = await self._client.get(key)
        if datetime_bytes is None:
            return None  # Если значение отсутствует, возвращаем None
        datetime_str = datetime_bytes.decode("utf-8")  # Асинхронное получение значения
        try:
            d = datetime.strptime(datetime_str, self.time_str_format)
        except:
            return None
        return d  # Преобразование строки в datetime

    async def get_invalid_norm_queries(self, adv_id: int, nmid: int) -> list[str]:
        key = self._get_invalid_norm_queries_key(adv_id, nmid)
        value = await self._client.get(key)
        if value is None:
            return []
        try:
            payload = json.loads(value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, str)]

    async def add_invalid_norm_queries(
        self, adv_id: int, nmid: int, phrases: list[str]
    ) -> list[str]:
        if not phrases:
            return await self.get_invalid_norm_queries(adv_id, nmid)
        existing = await self.get_invalid_norm_queries(adv_id, nmid)
        merged = list(dict.fromkeys([*existing, *phrases]))
        key = self._get_invalid_norm_queries_key(adv_id, nmid)
        await self._client.set(
            key,
            json.dumps(merged, ensure_ascii=False),
            ex=self.invalid_norm_query_ttl_seconds,
        )
        return merged
