import logging
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.client import Pipeline

from app.utils.text_cleaner import clear

from ..base_protocol import BaseRedisManagerProtocol

logger = logging.getLogger(__name__)


class PredictCTRRedisMixin(BaseRedisManagerProtocol):
    """Миксин для работы с ключами прогнозов CTR в Redis"""

    _client: Redis
    prefix = "predict_ctr"

    @property
    def key(self) -> str:
        """Свойство key для совместимости с базовым классом"""
        return self.prefix

    def get_key(self, *args: Any, **kwargs: Any) -> str:
        """Базовый метод для формирования ключа (логика в специализированных методах)"""
        return f"{self.prefix}:{':'.join(map(str, args))}"

    def _get_legacy_key(self, adv_id: int | str, keyword: str) -> str:
        """Формирование legacy ключа"""
        return f"predict_ctr:{adv_id}:{clear(keyword)}"

    def _get_new_key(self, nmids: list[int], keyword: str) -> str:
        """Формирование нового ключа по nmids"""
        sorted_nmids = sorted(nmids)
        nmids_str = ",".join(map(str, sorted_nmids))
        return f"predict_ctr_v2:{nmids_str}:{clear(keyword)}"

    async def set_predict_ctr_with_pipeline_legacy(
        self,
        redis_pipeline: Pipeline,
        adv_id: int | str,
        keyword: str,
        predict_ctr: float,
    ) -> None:
        """Legacy метод записи прогноза CTR в Redis"""
        key = self._get_legacy_key(adv_id, keyword)
        redis_pipeline.set(key, predict_ctr)

    async def set_predict_ctr_with_pipeline_by_nmids(
        self,
        redis_pipeline: Pipeline,
        nmids: list[int],
        keyword: str,
        predict_ctr: float,
    ) -> None:
        """Новый метод записи прогноза CTR в Redis по nmids"""
        key = self._get_new_key(nmids, keyword)
        redis_pipeline.set(key, predict_ctr)

    async def get_predict_ctr_by_nmids(self, nmids: list[int], keyword: str) -> float | None:
        """Чтение прогноза CTR из Redis по новому ключу"""
        key = self._get_new_key(nmids, keyword)
        return await self._get_predict_ctr_by_key(key)

    async def _get_predict_ctr_by_key(self, key: str) -> float | None:
        """Внутренний метод чтения прогноза CTR из Redis по ключу"""
        try:
            value = await self._client.get(key)
            if value is None:
                return None
            return float(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Ошибка преобразования значения CTR для ключа {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения CTR для ключа {key}: {e}")
            return None
