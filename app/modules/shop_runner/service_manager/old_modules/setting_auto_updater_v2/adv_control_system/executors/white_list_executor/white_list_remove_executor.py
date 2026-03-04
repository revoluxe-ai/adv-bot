"""Исполнитель для удаления ключевых слов из белого списка."""

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

logger = logging.getLogger(__name__)


class WhiteListRemoveExecutor(BaseExecutor):
    """Удаляет неэффективные ключевые слова из белого списка.

    Удаляет все ключи с pay_for_order выше целевого значения.
    При отсутствии валидных данных применяет анти-слив-стратегию.
    """

    async def execute(self, ctx: PipelineContext) -> ExecutionResult:
        """Удаляет неэффективные ключи из белого списка.

        Args:
            ctx: Контекст выполнения с планом, фактом и настройками

        Returns:
            ExecutionResult с результатом операции
        """
        adv_id = ctx.complex_adv.adv_setting.adv_id

        # Проверка включено ли управление белым списком
        if not ctx.complex_adv.is_white_list_control_enabled:
            logger.debug(
                "[adv_id=%s] WhiteListRemove: управление белым списком выключено, пропускаем",
                adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Получение keywords и фильтрация white_keywords
        keywords: list[CalculatedKeyword] = await ctx.complex_adv.get_keywords()
        white_keywords: list[CalculatedKeyword] = [
            kw for kw in keywords if kw.hard_status == 2 and not kw.best_keyword_status
        ]

        if not white_keywords:
            logger.debug(
                "[adv_id=%s] WhiteListRemove: нет ключей для удаления",
                adv_id,
            )
            return ExecutionResult(success=False, efficiency=0.0, used_power=0)

        # Определение target_pay_for_order из plan/fact
        target_pay_for_order = resolve_target_cost_from_context(ctx)

        # Приоритетная проверка режима раскрутки рекомендаций
        # Только если доступны данные о стоимости (plan/fact), иначе используем анти-слив
        if ctx.complex_adv.rec_system_promotion_mode_active and target_pay_for_order is not None:
            keywords_below_rec = self._filter_below_rec_conversion(white_keywords)
            if keywords_below_rec:
                # Логирование для каждого удаляемого ключа
                for kw in keywords_below_rec:
                    logger.info(
                        "[adv_id=%s] WhiteListRemove (RecMode): удаляем '%s' "
                        "(conversion=%.6f < rec_conversion, above_rec_conversion=False)",
                        adv_id,
                        kw.text,
                        kw.conv_views_to_orders,
                    )

                # Массовое удаление из белого списка
                keyword_ids = [kw.keyword_setting_original_id for kw in keywords_below_rec]
                stmt = (
                    update(KeywordSetting)
                    .where(KeywordSetting.id.in_(keyword_ids))
                    .values({"hard_status": 1})
                )
                await ctx.session.execute(stmt)
                await ctx.session.commit()

                removed_count = len(keywords_below_rec)
                total_white_count = len(white_keywords)
                efficiency = removed_count / total_white_count if total_white_count > 0 else 1.0

                logger.info(
                    "[adv_id=%s] WhiteListRemove (RecMode): успешно удалено %d ключей из БС",
                    adv_id,
                    removed_count,
                )

                return ExecutionResult(success=True, efficiency=efficiency, used_power=removed_count)

        # Ветвление логики в зависимости от наличия валидных данных
        if target_pay_for_order is not None:
            # Нормальный режим: удаляем ключи с превышающим pay_for_order
            keywords_to_remove = self._filter_ineffective_keywords(
                white_keywords, target_pay_for_order
            )

            if not keywords_to_remove:
                logger.debug(
                    "[adv_id=%s] WhiteListRemove: нет ключей с pay_for_order > %.2f",
                    adv_id,
                    target_pay_for_order,
                )
                return ExecutionResult(success=False, efficiency=0.0, used_power=0)

            # Логирование для каждого удаляемого ключа
            for kw in keywords_to_remove:
                if kw.orders_per_1000_rub <= 0:
                    logger.info(
                        "[adv_id=%s] WhiteListRemove: удаляем '%s' (orders_per_1000_rub=0, нет заказов)",
                        adv_id,
                        kw.text,
                    )
                else:
                    logger.info(
                        "[adv_id=%s] WhiteListRemove: удаляем '%s' (pay_for_order=%.2f > target=%.2f)",
                        adv_id,
                        kw.text,
                        kw.pay_for_order,
                        target_pay_for_order,
                    )
        else:
            # Анти-слив-стратегия: удаляем все кроме лучшего
            logger.error(
                "[adv_id=%s] WhiteListRemove: target_pay_for_order недоступен, "
                "применяется анти-слив-стратегия (оставляем только лучший ключ)",
                adv_id,
            )

            keywords_to_remove = self._apply_anti_drain_strategy(white_keywords)

            logger.warning(
                "[adv_id=%s] WhiteListRemove: анти-слив удалено %d ключей из БС",
                adv_id,
                len(keywords_to_remove),
            )

        # Массовое удаление из белого списка
        if keywords_to_remove:
            keyword_ids = [kw.keyword_setting_original_id for kw in keywords_to_remove]
            stmt = (
                update(KeywordSetting)
                .where(KeywordSetting.id.in_(keyword_ids))
                .values({"hard_status": 1})
            )
            await ctx.session.execute(stmt)
            await ctx.session.commit()

            removed_count = len(keywords_to_remove)
            total_white_count = len(white_keywords)
            efficiency = removed_count / total_white_count if total_white_count > 0 else 1.0

            logger.info(
                "[adv_id=%s] WhiteListRemove: успешно удалено %d ключей из БС",
                adv_id,
                removed_count,
            )

            return ExecutionResult(success=True, efficiency=efficiency, used_power=removed_count)

        return ExecutionResult(success=False, efficiency=0.0, used_power=0)

    @staticmethod
    def _filter_ineffective_keywords(
        white_keywords: list[CalculatedKeyword],
        target_pay_for_order: float,
    ) -> list[CalculatedKeyword]:
        """Фильтрует ключи с pay_for_order выше целевого.

        Args:
            white_keywords: Список ключей в белом списке
            target_pay_for_order: Целевой pay_for_order

        Returns:
            Список ключей для удаления
        """
        keywords_to_remove: list[CalculatedKeyword] = []

        for kw in white_keywords:
            # Ключи без заказов (orders_per_1000_rub <= 0) удаляем в первую очередь
            if kw.orders_per_1000_rub <= 0:
                keywords_to_remove.append(kw)
                continue

            # Для ключей с заказами проверяем pay_for_order

            pay_for_order = kw.pay_for_order
            if pay_for_order is None or pay_for_order > target_pay_for_order:
                keywords_to_remove.append(kw)


        return keywords_to_remove

    @staticmethod
    def _filter_below_rec_conversion(
        white_keywords: list[CalculatedKeyword],
    ) -> list[CalculatedKeyword]:
        """Фильтрует ключи с конверсией ниже конверсии рекомендаций.

        Args:
            white_keywords: Список ключей в белом списке

        Returns:
            Список ключей для удаления (с above_rec_conversion = False)
        """
        return [
            kw for kw in white_keywords
            if kw.above_rec_conversion is False
        ]

    @staticmethod
    def _apply_anti_drain_strategy(
        white_keywords: list[CalculatedKeyword],
    ) -> list[CalculatedKeyword]:
        """Применяет анти-слив-стратегию: оставляет только лучший ключ.

        Args:
            white_keywords: Список ключей в белом списке

        Returns:
            Список ключей для удаления (все кроме лучшего)
        """
        if not white_keywords:
            return []

        # Находим лучший ключ по рейтингу (стратегия: конверсия или заказы на 1000₽)
        best_keyword = max(white_keywords, key=lambda kw: kw.rating or 0)

        # Удаляем все кроме лучшего
        keywords_to_remove = [kw for kw in white_keywords if kw != best_keyword]

        return keywords_to_remove




