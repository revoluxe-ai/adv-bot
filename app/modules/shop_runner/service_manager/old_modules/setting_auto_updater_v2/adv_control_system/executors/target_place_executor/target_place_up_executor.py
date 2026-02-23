"""Исполнитель для повышения целевой позиции (уменьшение номера позиции)."""

import logging

from sqlalchemy import update

from app.modules.common_slaves.wildberries.models.enums import TargetPositionMode
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ExecutionResult,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.base_executor import (
    BaseExecutor,
)
from .redis_cache import LastTargetPlaceUpV2
from . import utils


logger = logging.getLogger(__name__)


class TargetPlaceUpExecutor(BaseExecutor):
    """Повышает целевую позицию на 1 (уменьшает номер, увеличивает охват)."""

    PASS_TIME_SECONDS = 15 * 60  # 15 минут между изменениями
    MIN_PLACE = 300  # Максимальное повышение
    MAX_PLACE = 1  # Минимальное повышение

    # TODO: Тут нужно получить максимальную ставку. Если текущая ставка равна максимальной, то смысла повышать позицию нет.
    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        """Повышает целевую позицию (decrease number).

        Args:
            ctx: Контекст выполнения

        Returns:
            ExecutionResult с результатом операции
        """

        complex_adv = ctx.complex_adv
        if complex_adv.individual_keywords_target_place_mode:
            result = await self._set_max_conv_mode(ctx)
            return result

        current_cpm = utils.get_current_cpm(complex_adv)
        if current_cpm is None:
            logger.debug(
                "[adv_id=%s] TargetPlaceDown: текущая ставка не установлена",
                ctx.complex_adv.adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        if not ctx.complex_adv.is_target_position_control_enabled:
            logger.debug(
                "[adv_id=%s] TargetPlaceUp: управление целевой позицией выключено, пропускаем",
                ctx.complex_adv.adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        redis_cache = LastTargetPlaceUpV2(ctx.complex_adv.adv_setting)

        # Проверка rate-limiting
        if not await redis_cache.check_pass_time(self.PASS_TIME_SECONDS):
            logger.debug(
                "[adv_id=%s] TargetPlaceUp: rate-limit не прошёл",
                ctx.complex_adv.adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        current_place = ctx.complex_adv.target_place

        if not current_place:
            logger.debug(
                "[adv_id=%s] TargetPlaceUp: целевая позиция не установлена",
                ctx.complex_adv.adv_id,
            )
            return ExecutionResult(success=False, efficiency=0, used_power=0)

        # Проверка лимита
        if current_place <= self.MAX_PLACE:  # маленькое число - выше позиция
            logger.debug(
                "[adv_id=%s] TargetPlaceUp: достигнут максимум (current=%s, min=%s)",
                ctx.complex_adv.adv_id,
                current_place,
                self.MIN_PLACE,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)
        # TODO: Вынести все условия, при которых функции автоапдейта выполняться не могут в отдельную функцию и задействовать ее при расчете тарифа
        max_cpm = await utils.get_max_cpm(ctx.complex_adv)
        if not max_cpm:
            logger.debug(
                "[adv_id=%s] TargetPlaceUp: не удалось получить максимальную ставку",
                ctx.complex_adv.adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)
        if current_cpm >= max_cpm:
            logger.debug(
                "[adv_id=%s] TargetPlaceUp: текущая ставка равна или превышает максимальную (current_cpm=%.2f, max_cpm=%.2f), повышение позиции не имеет смысла",
                ctx.complex_adv.adv_id,
                current_cpm,
                max_cpm,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Повышаем позицию на 1 (уменьшаем номер)
        new_place = max(current_place - 1, self.MAX_PLACE)

        # Обновляем в БД
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == ctx.complex_adv.db_id)
            .values({"max_place": new_place})
        )
        _ = await ctx.session.execute(stmt)
        await ctx.session.commit()
        await redis_cache.set()

        logger.info(
            "[adv_id=%s] TargetPlaceUp: %s -> %s",
            ctx.complex_adv.adv_id,
            current_place,
            new_place,
        )

        # Efficiency = 1 (выполнили одно изменение на 1)
        return ExecutionResult(success=True, efficiency=1.0, used_power=1)

    @staticmethod
    async def _set_max_conv_mode(ctx: PipelineContext) -> ExecutionResult:
        if ctx.complex_adv.target_position_mode == TargetPositionMode.MAX_CART_TO_VIEWS_CONV:
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)
        stmt = update(AdvSetting).where(AdvSetting.id == ctx.complex_adv.adv_setting_original_id) \
            .values({'target_position_mode': TargetPositionMode.MAX_CART_TO_VIEWS_CONV})
        await ctx.session.execute(stmt)
        await ctx.session.commit()
        return ExecutionResult(success=True, efficiency=1.0, used_power=1)
