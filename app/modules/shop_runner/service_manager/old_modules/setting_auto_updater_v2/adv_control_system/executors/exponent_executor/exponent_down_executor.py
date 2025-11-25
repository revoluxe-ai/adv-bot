"""Исполнитель для понижения экспоненты (увеличивает охват/расход)."""

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
from .redis_cache import LastExponentDownV2

from ..exponent_executor.utils.get_next_down_exponent import get_next_down_exponent


logger = logging.getLogger(__name__)


class ExponentDownExecutor(BaseExecutor):
    """Понижает экспоненту на 1 единицу (увеличивает охват и расход)."""

    PASS_TIME_SECONDS = 15 * 60  # 15 минут между изменениями
    MIN_EXPONENT = 1.0
    MAX_EXPONENT = 20.0

    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        """Понижает экспоненту на 1.

        Args:
            ctx: Контекст выполнения

        Returns:
            ExecutionResult с результатом операции
        """
        if not ctx.complex_adv.is_exponent_control_enabled:
            logger.debug(
                "[adv_id=%s] ExponentDown: управление экспонентой выключено, пропускаем",
                ctx.complex_adv.adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        redis_cache = LastExponentDownV2(ctx.complex_adv.adv_setting)

        # Проверка rate-limiting
        if not await redis_cache.check_pass_time(self.PASS_TIME_SECONDS):
            logger.debug(
                "[adv_id=%s] ExponentDown: rate-limit не прошёл", ctx.complex_adv.adv_id
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        current_exponent = ctx.complex_adv.exponent_predict_ctr

        # Проверка лимита
        if current_exponent <= self.MIN_EXPONENT:
            logger.debug(
                "[adv_id=%s] ExponentDown: достигнут минимум (current=%.2f, min=%.2f)",
                ctx.complex_adv.adv_id,
                current_exponent,
                self.MIN_EXPONENT,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)
        keywords = await ctx.complex_adv.get_keywords()
        # Понижаем экспоненту
        new_exponent = get_next_down_exponent(current_exponent, keywords)

        if new_exponent is None:
            logger.debug(
                "[adv_id=%s] ExponentDown: не удалось рассчитать новый шаг",
                ctx.complex_adv.adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        if new_exponent == current_exponent:
            logger.debug(
                "[adv_id=%s] ExponentDown: экспонента не изменится",
                ctx.complex_adv.adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Обновляем в БД
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == ctx.complex_adv.db_id)
            .values({"exponent_predict_ctr": new_exponent})
        )
        _ = await ctx.session.execute(stmt)
        await redis_cache.set()

        logger.info(
            "[adv_id=%s] ExponentDown: %.2f -> %.2f",
            ctx.complex_adv.adv_id,
            current_exponent,
            new_exponent,
        )

        # Efficiency зависит от величины изменения, на первом этапе просто 1
        return ExecutionResult(success=True, efficiency=1.0, used_power=1)
