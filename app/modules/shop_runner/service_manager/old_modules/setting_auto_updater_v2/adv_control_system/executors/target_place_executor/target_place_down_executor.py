"""Исполнитель для понижения целевой позиции (увеличение номера позиции)."""

import logging
from typing_extensions import override

from sqlalchemy import update

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ExecutionResult,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.base_executor import (
    BaseExecutor,
)
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

        redis_cache = LastTargetPlaceDownV2(ctx.complex_adv.adv_setting)
        # Проверка rate-limiting
        if not await redis_cache.check_pass_time(self.PASS_TIME_SECONDS):
            logger.debug(
                "[adv_id=%s] TargetPlaceDown: rate-limit не прошёл", adv_id
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)



        current_target_place: int = ctx.complex_adv.target_place


        if not current_target_place:
            logger.debug(
                "[adv_id=%s] TargetPlaceDown: целевая позиция не установлена", adv_id
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Проверка лимита
        if current_target_place >= self.MIN_PLACE: # нижнее место, большое число
            logger.debug(
                "[%s] TargetPlaceDown: достигнут минимум (current=%s, max=%s)",
                adv_id,
                current_target_place,
                self.MIN_PLACE,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Понижаем позицию на 1 (увеличиваем номер)
        new_place = min(current_target_place + 1, self.MIN_PLACE)  # MIN_PLACE - это нижнее значение, большое число

        best_keyword: CalculatedKeyword | None = await utils.get_best_keyword(ctx.complex_adv)
        if not best_keyword:
            logger.debug(
                "[adv_id=%s] TargetPlaceDown: не удалось получить лучший ключевик",
                adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)


        current_position = best_keyword.position
        if current_position is None:
            raise RuntimeError('current_position не может быть None здесь т.к. такое отфильтровали в utils.get_best_keyword')
        if current_position == 0 or current_position + 1 < new_place:  # логика в том, что если товар не спускается, то смысла нет дальше снижать ЦП
            logger.debug(
                "[adv_id=%s] TargetPlaceDown: текущее место (%s) уже ниже или равно новому целевому месту (%s), понижение не имеет смысла",
                adv_id,
                current_position,
                new_place,
            )
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

        # Efficiency = 1 (выполнили одно изменение на 1)
        return ExecutionResult(success=True, efficiency=1.0, used_power=1)
