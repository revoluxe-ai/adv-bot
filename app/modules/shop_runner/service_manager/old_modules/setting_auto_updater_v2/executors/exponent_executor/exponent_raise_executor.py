"""Исполнитель для повышения экспоненты (снижает охват/расход)."""

import logging

from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.data_classes import (
    ExecutionResult,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.executors.base_executor import (
    BaseExecutor,
)
from .redis_cache import LastExponentRaiseV2

logger = logging.getLogger(__name__)


class ExponentRaiseExecutor(BaseExecutor):
    """Повышает экспоненту на 1 единицу (снижает охват и расход)."""

    PASS_TIME_SECONDS = 15 * 60  # 15 минут между изменениями
    MIN_EXPONENT = 1.0
    MAX_EXPONENT = 20.0

    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        """Повышает экспоненту на 1.
        
        Args:
            ctx: Контекст выполнения
            
        Returns:
            ExecutionResult с результатом операции
        """
        redis_cache = LastExponentRaiseV2(ctx.adv)

        # Проверка rate-limiting
        if not await redis_cache.check_pass_time(self.PASS_TIME_SECONDS):
            logger.debug(
                f"[adv_id={ctx.adv.adv_id}] ExponentRaise: rate-limit не прошёл"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        current_exponent = ctx.adv.exponent_predict_ctr
        
        # Проверка лимита
        if current_exponent >= self.MAX_EXPONENT:
            logger.debug(
                f"[adv_id={ctx.adv.adv_id}] ExponentRaise: достигнут максимум "
                f"(current={current_exponent}, max={self.MAX_EXPONENT})"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Повышаем на 1 (на первом этапе всегда шаг = 1)
        new_exponent = min(current_exponent + 1.0, self.MAX_EXPONENT)

        # Обновляем в БД
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == ctx.adv.id)
            .values({"exponent_predict_ctr": new_exponent})
        )
        await ctx.session.execute(stmt)
        await redis_cache.set()

        logger.info(
            f"[adv_id={ctx.adv.adv_id}] ExponentRaise: "
            f"{current_exponent:.2f} → {new_exponent:.2f}"
        )

        # Efficiency = 1 (выполнили одно изменение на 1)
        return ExecutionResult(success=True, efficiency=1.0, used_power=1)

