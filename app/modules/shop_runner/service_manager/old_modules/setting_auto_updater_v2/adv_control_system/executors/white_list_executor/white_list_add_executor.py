"""Исполнитель для добавления ключевых слов в белый список."""

import logging
from sqlalchemy import update
from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ExecutionResult,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.base_executor import (
    BaseExecutor,
)
from app.shared.domains.wb.utils.cost_resolver import (
    resolve_target_cost_from_context,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus

from .redis_cache import LastAutoAddPhraseToWhiteListV2

logger = logging.getLogger(__name__)


# TODO: Как промежуточный шаг сделать настройку мощности от 1 до 3 (по числу исполнителей)


class WhiteListAddExecutor(BaseExecutor):
    """Добавляет наиболее эффективные релевантные ключевые слова в белый список."""

    PASS_TIME_SECONDS = 15 * 60  # 15 минут между изменениями
    PAY_PER_ORDER_THRESHOLD = 0.9  # 90% от целевой себестоимости заказа

    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        """Добавляет один ключ в белый список.

        Args:
            ctx: Контекст выполнения

        Returns:
            ExecutionResult с результатом операции
        """
        redis_cache = LastAutoAddPhraseToWhiteListV2(ctx.complex_adv.adv_setting)

        # Проверка rate-limiting
        if not await redis_cache.check_pass_time(self.PASS_TIME_SECONDS):
            logger.debug(
                f"[adv_id={ctx.complex_adv.adv_id}] WhiteListAdd: rate-limit не прошёл"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Проверка себестоимости заказа (90% от целевой)
        target_cost = resolve_target_cost_from_context(ctx)
        if target_cost is None or target_cost <= 0:
            logger.warning(
                f"[adv_id={ctx.complex_adv.adv_id}] WhiteListAdd: невалидные данные план-факт, пропускаем"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)
        current_pay_for_order = ctx.fact.pay_for_order
        threshold = self.PAY_PER_ORDER_THRESHOLD * target_cost

        if current_pay_for_order >= threshold:
            logger.info(
                f"[adv_id={ctx.complex_adv.adv_id}] WhiteListAdd: пропуск из-за высокой себестоимости заказа "
                f"(текущая={current_pay_for_order:.2f}, порог={threshold:.2f} (90%), "
                f"целевая={target_cost:.2f}, {current_pay_for_order / target_cost * 100:.1f}%)"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        mean_auto_ctr: float | None = await ctx.complex_adv.get_mean_auto_ctr()

        # Фильтруем кандидатов для белого списка
        def candidate_filter(keyword: CalculatedKeyword) -> bool | None:
            base_ok = keyword.hard_status == 1 and keyword.status == KeywordStatus.BAD
            if not base_ok:
                return False
            if ctx.complex_adv.rec_system_promotion_mode_active and (
                keyword.above_rec_conversion is  not True
            ):
                return False
            if ctx.complex_adv.auto_add_only_relevant_phrase:
                return (
                    keyword.relevant
                    and (
                        keyword.ctr > mean_auto_ctr
                        if mean_auto_ctr is not None
                        else True
                    )
                )
            return True

        keywords = await ctx.complex_adv.get_keywords()
        candidates = list(filter(candidate_filter, keywords))

        if not candidates:
            logger.debug(
                f"[adv_id={ctx.complex_adv.adv_id}] WhiteListAdd: нет кандидатов для добавления"
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Сортируем по рейтингу и берём лучший
        candidates.sort(key=lambda kw: kw.rating_by_orders, reverse=True)
        best_keyword = candidates[0]

        # Добавляем в белый список
        stmt = (
            update(KeywordSetting)
            .where(KeywordSetting.id == best_keyword.keyword_setting_original_id)
            .values({"hard_status": 2})
        )
        await ctx.session.execute(stmt)
        await redis_cache.set()

        logger.info(
            f"[adv_id={ctx.complex_adv.adv_id}] WhiteListAdd: добавлен ключ '{best_keyword.text}' "
            f"(rating={best_keyword.rating_by_orders:.4f})"
        )

        # Efficiency = 1 ключ добавлен (на первом этапе всегда 1 действие)
        return ExecutionResult(success=True, efficiency=1.0, used_power=1)
