"""Каскадное выполнение исполнителей с передачей силы реакции."""

import logging

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.base_executor import (
    BaseExecutor,
)
from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase


class LastAdvControlSystemUpdate(
    AdvSettingRedisCache, RedisCacheBase, prefix="LastAdvControlSystemUpdate"
):
    """Redis-кэш для отслеживания последнего обновления кампании AdvControlSystem."""

    pass


logger = logging.getLogger(__name__)


class ControlCascade:
    """Последовательное выполнение adv-исполнителей с передачей силы."""

    def __init__(self, executors: list[BaseExecutor]):
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
        logger.info(
            f"[adv_id={ctx.adv.adv_id}] Запуск каскада: "
            f"state={ctx.state.name}, force={ctx.force.value}, "
            f"executors={len(self.executors)}"
        )

        for i, executor in enumerate(self.executors, 1):
            executor_name = executor.__class__.__name__

            logger.debug(
                f"[adv_id={ctx.adv.adv_id}] Исполнитель {i}/{len(self.executors)}: "
                f"{executor_name}, force={ctx.force.value}"
            )

            result = await executor.execute(ctx)

            logger.debug(
                f"[adv_id={ctx.adv.adv_id}] {executor_name}: "
                f"success={result.success}, efficiency={result.efficiency:.2f}, "
                f"used_power={result.used_power}"
            )

            # Ослабляем силу реакции
            ctx.force = ctx.force.weaken(result.efficiency)

            # Прерываем, если сила слишком мала
            if ctx.force.value <= 0:
                logger.info(
                    f"[adv_id={ctx.adv.adv_id}] Каскад прерван: "
                    f"сила реакции упала до {ctx.force.value}"
                )
                break

        # Коммитим все изменения
        await ctx.session.commit()

        # Обновляем глобальный кэш последнего обновления кампании
        last_update_cache = LastAdvControlSystemUpdate(ctx.adv)
        # await last_update_cache.set() # TODO: Закомментировано для отладки

        logger.info(
            f"[adv_id={ctx.adv.adv_id}] Каскад завершён, "
            f"оставшаяся сила={ctx.force.value}"
        )
