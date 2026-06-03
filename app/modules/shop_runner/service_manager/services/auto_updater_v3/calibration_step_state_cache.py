"""Redis-снимок adaptive calibration steps (direction + effective) для V3."""

from __future__ import annotations

import logging

from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
    CalibrationStepState,
)

logger = logging.getLogger(__name__)

_SEPARATOR = "|"


class V3CalibrationStepState(AdvSettingRedisCache, RedisCacheBase, prefix="V3CalibrationStepState"):
    """Последнее направление и effective steps калибратора на РК."""

    async def get_state(self) -> CalibrationStepState | None:
        """Прочитать состояние или ``None``, если ключ отсутствует / битый."""
        value_bytes: bytes | str | None = await self._client.get(self._key)
        if not value_bytes:
            return None
        if isinstance(value_bytes, bytes):
            raw = value_bytes.decode()
        else:
            raw = value_bytes
        try:
            eff_str, direct_str = raw.split(_SEPARATOR, maxsplit=1)
            effective_steps = int(eff_str)
            direct = CalibrationDirect(direct_str)
        except (ValueError, KeyError):
            logger.warning(
                "V3CalibrationStepState: invalid cached value adv_id=%s raw=%r",
                self._unique_id,
                raw,
            )
            return None
        if effective_steps < 1:
            return None
        return CalibrationStepState(effective_steps=effective_steps, direct=direct)

    async def set_state(self, state: CalibrationStepState) -> None:
        """Записать состояние после NORMAL-тика."""
        value = f"{int(state.effective_steps)}{_SEPARATOR}{state.direct.value}"
        await self._client.set(self._key, value)
