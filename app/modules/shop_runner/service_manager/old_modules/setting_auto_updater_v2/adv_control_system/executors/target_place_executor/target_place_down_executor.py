"""Исполнитель для понижения целевой позиции (увеличение номера позиции)."""

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
from .redis_cache import LastTargetPlaceDownV2

logger = logging.getLogger(__name__)


class TargetPlaceDownExecutor(BaseExecutor):
    """Понижает целевую позицию на 1 (увеличивает номер, снижает охват)."""

    PASS_TIME_SECONDS = 15 * 60  # 15 минут между изменениями
    MAX_PLACE = 1  # Максимальное повышение
    MIN_PLACE = 300  # Минимальное понижение

    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        """Понижает целевую позицию (increase number).

        Args:
            ctx: Контекст выполнения

        Returns:
            ExecutionResult с результатом операции
        """
        redis_cache = LastTargetPlaceDownV2(ctx.adv)

        # Проверка rate-limiting
        if not await redis_cache.check_pass_time(self.PASS_TIME_SECONDS):
            logger.debug(
                f"[adv_id={ctx.adv.adv_id}] TargetPlaceDown: rate-limit не прошёл"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        current_place = ctx.adv.max_place

        if not current_place:
            logger.debug(
                f"[adv_id={ctx.adv.adv_id}] TargetPlaceDown: целевая позиция не установлена"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Проверка лимита
        if current_place >= self.MAX_PLACE:
            logger.debug(
                f"[adv_id={ctx.adv.adv_id}] TargetPlaceDown: достигнут минимум "
                f"(current={current_place}, max={self.MAX_PLACE})"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Понижаем позицию на 1 (увеличиваем номер)
        new_place = min(current_place + 1, self.MAX_PLACE)

        # Обновляем в БД
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == ctx.adv.id)
            .values({"max_place": new_place})
        )
        await ctx.session.execute(stmt)
        await redis_cache.set()

        logger.info(
            f"[adv_id={ctx.adv.adv_id}] TargetPlaceDown: {current_place} → {new_place}"
        )

        # Efficiency = 1 (выполнили одно изменение на 1)
        return ExecutionResult(success=True, efficiency=1.0, used_power=1)
