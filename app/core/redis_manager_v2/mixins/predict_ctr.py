import logging
from typing import Any

from redis.asyncio.client import Pipeline

from app.modules.common_slaves.wildberries.models.models import (
    AdvSetting,
    PredictCTRMode,
)
from app.utils.text_cleaner import clear

logger = logging.getLogger(__name__)


class PredictCTRRedisMixin:
    """Миксин для работы с ключами прогнозов CTR в Redis"""

    prefix = "predict_ctr"

    # `_client` инициализируется в классах, которые используют этот миксин.
    # Объявляем атрибут для корректной проверки типизации (mypy).
    _client: Any

    def _get_key(self, adv: AdvSetting, keyword: str) -> str:
        if not adv.predict_ctr_mode or adv.predict_ctr_mode == PredictCTRMode.V1:
            return self._get_key_v1(adv.adv_id, keyword)
        elif adv.predict_ctr_mode == PredictCTRMode.V2:
            return self._get_key_v2(adv.nmids, keyword)
        else:
            raise ValueError("Не верно указана версия predict_ctr_mode")

    def _get_key_v1(self, adv_id: int, keyword: str) -> str:
        """Формирование legacy ключа"""
        return f"predict_ctr:{adv_id}:{clear(keyword)}"

    def _get_key_v2(self, nmids: list[int], keyword: str) -> str:
        """Формирование нового ключа по nmids"""
        sorted_nmids = sorted(nmids)
        nmids_str = ",".join(map(str, sorted_nmids))
        return f"predict_ctr_v2:{nmids_str}:{clear(keyword)}"

    async def set_predict_ctr_with_pipeline(
        self,
        redis_pipeline: Pipeline,
        adv: AdvSetting,
        keyword: str,
        predict_ctr: float,
    ) -> None:
        """Новый метод записи прогноза CTR в Redis по nmids"""
        key = self._get_key(adv, keyword)
        redis_pipeline.set(key, predict_ctr)

    async def get_predict_ctr(self, adv: AdvSetting, keyword: str) -> float | None:
        """Чтение прогноза CTR из Redis по новому ключу"""
        key = self._get_key(adv, keyword)
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
