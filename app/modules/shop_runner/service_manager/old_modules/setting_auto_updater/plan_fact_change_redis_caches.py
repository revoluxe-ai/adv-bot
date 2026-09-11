import json
import logging

from pydantic import ValidationError

from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)

logger = logging.getLogger(__name__)


class ChangePlanFact(AdvSettingRedisCache, RedisCacheBase, prefix="ChangePlanFact"):
    async def check_equal_in_cache(self, plan: PlanData, fact: FactData) -> bool:
        value_bytes: bytes | str | None = await self._client.get(self._key)
        if not value_bytes:
            return False
        # TODO: Упало на Smoke тестах. Проблема в том. что новый Redis кэш возвращает не bytes, а str, старый - bytes\r
        if isinstance(
            value_bytes, bytes
        ):  # pyright: ignore[reportUnnecessaryIsInstance]
            value: str = value_bytes.decode()
        else:
            value = value_bytes
        try:
            old_plan_value, old_fact_value = value.split("|")
        except ValueError:
            return False
        try:
            old_plan = PlanData.model_validate_json(old_plan_value)
            old_fact = FactData.model_validate_json(old_fact_value)
        except ValidationError:
            return False
        return self._equal_plan(plan, old_plan) and self._equal_fact(fact, old_fact)

    async def set_new_plan_fact(self, plan: PlanData, fact: FactData) -> None:
        key = self._key
        plan_value: str = json.dumps(plan.model_dump(mode="json"))
        fact_value: str = json.dumps(fact.model_dump(mode="json"))
        value = f"{plan_value}|{fact_value}"
        await self._client.set(key, value)

    async def clear_cached_plan_fact(self) -> None:
        """Сброс snapshot plan/fact (например после смены плана в PG без V3-тика)."""
        await self._client.delete(self._key)

    def _equal_plan(self, plan: PlanData, old_plan: PlanData) -> bool:
        return plan == old_plan

    def _equal_fact(self, fact: FactData, old_fact: FactData) -> bool:
        return all(
            [
                fact.original_orders == old_fact.original_orders,
                fact.pay_for_order == old_fact.pay_for_order,
            ]
        )


async def clear_change_plan_fact_cache(adv_id: int) -> None:
    """Сброс ``ChangePlanFact:{adv_id}`` без загрузки ``AdvSetting`` из PG."""
    from types import SimpleNamespace

    ref = SimpleNamespace(adv_id=int(adv_id))
    await ChangePlanFact(ref).clear_cached_plan_fact()  # type: ignore[arg-type]
