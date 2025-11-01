"""Исполнитель для повышения целевой позиции (уменьшение номера позиции)."""

import logging

from sqlalchemy import update

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ExecutionResult,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.base_executor import (
    BaseExecutor,
)
from .redis_cache import LastTargetPlaceUpV2

logger = logging.getLogger(__name__)


class TargetPlaceUpExecutor(BaseExecutor):
    """Повышает целевую позицию на 1 (уменьшает номер, увеличивает охват)."""

    PASS_TIME_SECONDS = 15 * 60  # 15 минут между изменениями
    MIN_PLACE = 1  # Максимальное повышение
    MAX_PLACE = 300  # Минимальное повышение

    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        """Повышает целевую позицию (decrease number).

        Args:
            ctx: Контекст выполнения

        Returns:
            ExecutionResult с результатом операции
        """
        redis_cache = LastTargetPlaceUpV2(ctx.adv)

        # Проверка rate-limiting
        if not await redis_cache.check_pass_time(self.PASS_TIME_SECONDS):
            logger.debug(
                f"[adv_id={ctx.adv.adv_id}] TargetPlaceUp: rate-limit не прошёл"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        current_place = ctx.adv.max_place

        if not current_place:
            logger.debug(
                f"[adv_id={ctx.adv.adv_id}] TargetPlaceUp: целевая позиция не установлена"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Проверка лимита
        if current_place <= self.MIN_PLACE:
            logger.debug(
                f"[adv_id={ctx.adv.adv_id}] TargetPlaceUp: достигнут максимум "
                f"(current={current_place}, min={self.MIN_PLACE})"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Повышаем позицию на 1 (уменьшаем номер)
        new_place = max(current_place - 1, self.MIN_PLACE)

        # Обновляем в БД
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == ctx.adv.id)
            .values({"max_place": new_place})
        )
        await ctx.session.execute(stmt)
        await redis_cache.set()

        logger.info(
            f"[adv_id={ctx.adv.adv_id}] TargetPlaceUp: {current_place} → {new_place}"
        )

        # Efficiency = 1 (выполнили одно изменение на 1)
        return ExecutionResult(success=True, efficiency=1.0, used_power=1)
