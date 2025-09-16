from datetime import datetime

from app.core.redis_manager.base_redis_manager import BaseRedis


class KeywordStatUpdateState(BaseRedis):
    time_str_format = "%d-%m-%Y %H:%M:%S"

    @staticmethod
    def _get_key(adv_id: int) -> str:
        """
        Формирует ключ для хранения данных в Redis.
        """
        return f"adv_keyword_stat_update:{adv_id}"

    async def set_one(self, adv_id: int) -> None:
        """
        Сохраняет метку времени обновления в Redis.

        :param adv_id: ID рекламы.
        :param update_time_stamp: Момент времени обновления.
        """
        key = self._get_key(adv_id)
        update_time_stamp = datetime.now()
        datetime_str = update_time_stamp.strftime(self.time_str_format)  # Преобразование в строку
        await self._client.set(key, datetime_str)  # Асинхронная установка значения

    async def get_one(self, adv_id: int) -> datetime | None:
        """
        Получает метку времени обновления из Redis.

        :param adv_id: ID рекламы.
        :return: Момент времени обновления.
        """
        key = self._get_key(adv_id)
        datetime_bytes = await self._client.get(key)  # Асинхронное получение значения
        if datetime_bytes is None:
            return None  # Если значение отсутствует, возвращаем None
        datetime_str = datetime_bytes.decode("utf-8")
        try:
            dt = datetime.strptime(datetime_str, self.time_str_format)
        except:
            return None
        return dt
