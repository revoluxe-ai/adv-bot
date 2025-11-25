"""Каскадное выполнение исполнителей с передачей силы реакции."""

import logging
from collections.abc import Sequence

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.base_executor import (
    BaseExecutor,
)
from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.mixins.data_types.pass_time_redis_cache_base import (
    PassTimeRedisCacheBase,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase


class LastAdvControlSystemUpdate(  # pyright: ignore[reportIncompatibleVariableOverride]
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastAdvControlSystemUpdate",
):
    """Redis-кэш для отслеживания последнего обновления кампании AdvControlSystem."""

    pass


logger = logging.getLogger(__name__)


class ControlCascade:
    """Последовательное выполнение adv-исполнителей с передачей силы."""

    def __init__(self, executors: Sequence[BaseExecutor]):
        """
        Args:
            executors: Список исполнителей для последовательного выполнения
        """
        self.executors = executors

    async def run(self, ctx: PipelineContext) -> None:
        """Выполняет каскад исполнителей.

        Каждый исполнитель:
        1. Выполняет своё действие
        2. Возвращает результат с efficiency
        3. Сила реакции ослабляется на efficiency
        4. Если сила <= 5, каскад прерывается

        Args:
            ctx: Контекст выполнения с данными кампании
        """

        for executor in self.executors:
            result = await executor.execute(ctx)
            # Ослабляем силу реакции
            ctx.force = ctx.force.weaken(result.efficiency)
            # Прерываем, если сила слишком мала
            if ctx.force.value <= 0:
                break
        # Коммитим все изменения

        # Обновляем глобальный кэш последнего обновления кампании
        last_update_cache = LastAdvControlSystemUpdate(ctx.complex_adv.adv_setting)
        await last_update_cache.set()  # TODO: Закомментировано для отладки
