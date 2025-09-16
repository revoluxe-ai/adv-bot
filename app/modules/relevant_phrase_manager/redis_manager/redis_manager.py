import json

from app.core.redis_manager.base_redis_manager import BaseRedis
from app.modules.common_slaves.wildberries.models import AdvSetting


class RedisManager(BaseRedis):
    def __init__(self, adv: AdvSetting):
        self._adv = adv

    @property
    def key(self) -> str:
        adv_setting_original_id = self._adv
        key = "black_phrases:" + str(adv_setting_original_id)
        return key

    @staticmethod
    def _is_legacy_format(data: str) -> bool:
        """Проверяет, является ли строка старым CSV-форматом."""
        return not data.startswith("[") and not data.startswith(
            "{"
        )  # не JSON-массив и не JSON-объект

    async def set_black_phrases(self, black_phrases: list[str]) -> None:
        """Сохраняет фразы в новом JSON-формате."""
        await self.client.set(self.key, json.dumps(black_phrases))

    async def get_black_phrases(self) -> list[str]:
        """Получает фразы, автоматически конвертируя старый формат в новый."""
        answer = await self.client.get(self.key)

        if not answer or answer == b"":
            return []

        data = answer.decode("utf-8")

        if self._is_legacy_format(data):
            # Конвертируем старый CSV-формат в новый JSON-формат
            phrases = data.split(",")
            await self.set_black_phrases(phrases)  # Миграция на новый формат
            return phrases
        else:
            # Это уже JSON, просто парсим
            return json.loads(data)

    @staticmethod
    def is_template_with_condition(phrase: str) -> bool:
        """Проверяет, содержит ли фраза условие (NOT:, ANY: и т.д.)."""
        return any(phrase.startswith(prefix) for prefix in ("NOT:", "ANY:"))
