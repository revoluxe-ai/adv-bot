import asyncio
import time
from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)


class FactDataCache:
    def __init__(self, ttl_seconds: float = 15 * 60) -> None:
        self._ttl_seconds = ttl_seconds
        self._cache: dict[int, tuple[FactData, float]] = {}
        self._inflight: dict[int, asyncio.Task[FactData]] = {}
        self._lock = asyncio.Lock()

    async def get_fact_data(
        self,
        adv: ComplexAdv,
        *,
        keywords: list[CalculatedKeyword] | None = None,
    ) -> FactData:
        cached = self._cache.get(adv.adv_id)
        if cached is not None and not self._is_expired(cached[1]):
            return cached[0]
        async with self._lock:
            cached = self._cache.get(adv.adv_id)
            if cached is not None and not self._is_expired(cached[1]):
                return cached[0]
            self._cache.pop(adv.adv_id, None)
            inflight = self._inflight.get(adv.adv_id)
            if inflight is None:
                inflight = asyncio.create_task(
                    self._build_fact_data(adv, keywords=keywords)
                )
                self._inflight[adv.adv_id] = inflight
        fact = await inflight
        async with self._lock:
            self._cache[adv.adv_id] = (fact, time.time())
            self._inflight.pop(adv.adv_id, None)
        return fact

    async def _build_fact_data(
        self,
        adv: ComplexAdv,
        *,
        keywords: list[CalculatedKeyword] | None = None,
    ) -> FactData:
        if keywords is None:
            keywords = await adv.get_keywords()
        provider = PlanFactProvider(adv.adv_setting)
        return await provider.get_fact_data(keywords)

    def _is_expired(self, timestamp: float) -> bool:
        return (time.time() - timestamp) > self._ttl_seconds


async def get_fact_data_for_adv(
    adv: ComplexAdv,
    *,
    keywords: list[CalculatedKeyword] | None = None,
    cache: FactDataCache | None = None,
) -> FactData:
    if cache is None:
        provider = PlanFactProvider(adv.adv_setting)
        if keywords is None:
            keywords = await adv.get_keywords()
        return await provider.get_fact_data(keywords)
    return await cache.get_fact_data(adv, keywords=keywords)
