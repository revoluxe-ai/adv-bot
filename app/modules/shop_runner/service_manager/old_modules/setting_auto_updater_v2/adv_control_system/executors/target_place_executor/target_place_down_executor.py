"""Исполнитель для понижения целевой позиции (увеличение номера позиции)."""

import logging
from typing_extensions import override

from sqlalchemy import update


from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ExecutionResult,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.base_executor import (
    BaseExecutor,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from .redis_cache import LastTargetPlaceDownV2

from . import utils

logger = logging.getLogger(__name__)


class TargetPlaceDownExecutor(BaseExecutor):
    """Понижает целевую позицию на 1 (увеличивает номер, снижает охват)."""

    PASS_TIME_SECONDS: int = 15 * 60  # 15 минут между изменениями
    MAX_PLACE: int = 1  # Максимальное повышение
    MIN_PLACE: int = 300  # Минимальное понижение

    # TODO: Если Текущая позиция больше или равна той, на которую хотим понизить, то не понижаем, смысла нет
    @override
    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        """Понижает целевую позицию (increase number).

        Args:
            ctx: Контекст выполнения

        Returns:
            ExecutionResult с результатом операции
        """

        adv_setting: AdvSetting = ctx.complex_adv.adv_setting
        adv_id = adv_setting.adv_id
        if not ctx.complex_adv.is_target_position_control_enabled:
            logger.debug(
                "[adv_id=%s] TargetPlaceDown: управление целевой позицией выключено, пропускаем",
                adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)
        min_place_by_keywords: int = await self._get_min_place_by_keywords(ctx)
        redis_cache = LastTargetPlaceDownV2(ctx.complex_adv.adv_setting)
        # Проверка rate-limiting
        if not await redis_cache.check_pass_time(self.PASS_TIME_SECONDS):
            logger.debug("[adv_id=%s] TargetPlaceDown: rate-limit не прошёл", adv_id)
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        current_target_place: int = ctx.complex_adv.target_place

        if not current_target_place:
            logger.debug(
                "[adv_id=%s] TargetPlaceDown: целевая позиция не установлена", adv_id
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Проверка лимита
        if current_target_place >= self.MIN_PLACE:  # нижнее место, большое число
            logger.debug(
                "[%s] TargetPlaceDown: достигнут минимум (current=%s, max=%s)",
                adv_id,
                current_target_place,
                self.MIN_PLACE,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Понижаем позицию на 1 (увеличиваем номер)
        new_place = min(
            current_target_place + 1, self.MIN_PLACE, min_place_by_keywords
        )

        if new_place == current_target_place:
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

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
            "[adv_id=%s] TargetPlaceDown: %s -> %s",
            adv_id,
            current_target_place,
            new_place,
        )
        if new_place < current_target_place:
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)
        # Efficiency = 1 (выполнили одно изменение на 1)
        return ExecutionResult(success=True, efficiency=1.0, used_power=1)
