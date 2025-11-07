"""Исполнитель для удаления ключевых слов из белого списка."""

import logging

from sqlalchemy import update

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ExecutionResult,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.base_executor import (
    BaseExecutor,
)
from .redis_cache import LastAutoDeleteFromWhiteListV2

logger = logging.getLogger(__name__)


class WhiteListRemoveExecutor(BaseExecutor):
    """Удаляет наименее эффективные ключевые слова из белого списка."""

    PASS_TIME_SECONDS = 15 * 60  # 15 минут между изменениями

    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        """Удаляет один ключ из белого списка.

        Args:
            ctx: Контекст выполнения

        Returns:
            ExecutionResult с результатом операции
        """
        adv_id = ctx.complex_adv.adv_setting.adv_id
        if not ctx.complex_adv.is_white_list_control_enabled:
            logger.debug(
                "[adv_id=%s] WhiteListRemove: управление белым списком выключено, пропускаем",
                adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)
        adv_setting: AdvSetting = ctx.complex_adv.adv_setting
        redis_cache = LastAutoDeleteFromWhiteListV2(adv_setting)

        # Проверка rate-limiting
        if not await redis_cache.check_pass_time(self.PASS_TIME_SECONDS):
            logger.debug(
                "[adv_id=%s] WhiteListRemove: rate-limit не прошёл", ctx.complex_adv.adv_id
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)
        keywords: list[CalculatedKeyword] = await ctx.complex_adv.get_keywords()
        # Фильтруем ключи в белом списке (hard_status=2), кроме best_keyword
        white_keywords: list[CalculatedKeyword] = [
            kw
            for kw in keywords
            if kw.hard_status == 2 and not kw.best_keyword_status
        ]    

        if not white_keywords:
            logger.debug(
                "[adv_id=%s] WhiteListRemove: нет ключей для удаления", ctx.complex_adv.adv_id
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        def sort_func(kw: CalculatedKeyword) -> float:
            return kw.predict_ctr or 0

        # Сортируем по базовому CTR и оставляем всех кроме лучшего
        white_keywords.sort(key=sort_func, reverse=True) # тут было по баесу, заменил на predict_ctr
        white_keywords = white_keywords[1:]  # Убираем лучший ключ из кандидатов

        if not white_keywords:
            logger.debug(
                "[adv_id=%s] WhiteListRemove: только один ключ в БС, не удаляем",
                ctx.complex_adv.adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Берём худший ключ для удаления
        worst_keyword = white_keywords[-1]

        # Удаляем из белого списка
        stmt = (
            update(KeywordSetting)
            .where(KeywordSetting.id == worst_keyword.keyword_setting_original_id)
            .values({"hard_status": 1})
        )
        _ = await ctx.session.execute(stmt)
        await ctx.session.commit()
        await redis_cache.set()

        logger.info(
            "[adv_id=%s] WhiteListRemove: удалён ключ '%s' (base_ctr=%.4f)",
            ctx.complex_adv.adv_id,
            worst_keyword.text,
            worst_keyword.baes_ctr,
        )

        # Efficiency = 1 ключ удалён (на первом этапе всегда 1 действие)
        return ExecutionResult(success=True, efficiency=1.0, used_power=1)
        