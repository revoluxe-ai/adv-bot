from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.modules.common_advs_stat import CommonAdvsStatData, CommonAdvsStatDataManager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.fact_sales_delta_manager import (
    FactSalesDeltaManager,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
        PlanFactSummary,
    )


class PlanFactProvider:
    def __init__(
        self,
        adv: AdvSetting,
        max_last_period: int = 2,
        fact_sales_manager: FactSalesDeltaManager | None = None,
    ):
        self._adv = adv
        self._max_last_period = max_last_period
        self._fact_sales_manager = fact_sales_manager or FactSalesDeltaManager()

    async def try_get_incremental_fact_data(self) -> FactData | None:
        """Пытается получить факт из инкрементальных снапшотов без расчёта stat."""
        if not self._adv.use_incremental_stats:
            return None
        fact_data: FactData | None = await self._fact_sales_manager.calculate_fact_data(
            self._adv.adv_id,
            self._adv.sales_predict_method,
            self._adv.nmids,
        )
        return fact_data

    async def get_fact_data(
        self, stat: CommonAdvsStatData
    ) ->FactData:
        fact_data = await self.try_get_incremental_fact_data()
        if fact_data is not None:
            return fact_data
        return self._get_fact_data_from_stat(stat)


    async def get_stat_data(
        self, keywords: list[CalculatedKeyword]
    ) -> CommonAdvsStatData:
        common_stat_manager = CommonAdvsStatDataManager()
        return await common_stat_manager.get_data(
            self._adv, keywords, last_days=self._max_last_period
        )

    @staticmethod
    def fact_data_from_plan_fact_summary(
        summary: PlanFactSummary | None,
        adv_setting: AdvSetting,
    ) -> FactData | None:
        """Собирает FactData из последнего снимка в ClickHouse (plan_fact_stats).

        Реализация в ``plan_fact_reader``; ленивый импорт, чтобы не зациклить
        загрузку ``PlanFactProvider`` с ``wb_shop_data_manager``.
        Важно: целевые значения (plan/target/max) берутся не из CH-сводки,
        а из текущих настроек ``AdvSetting`` через ``get_plan_data``.
        """
        from app.modules.shop_runner.service_manager.services.plan_fact_controller import (
            plan_fact_reader,
        )

        return plan_fact_reader.fact_data_from_plan_fact_summary(
            summary, adv_setting
        )

    @staticmethod
    def _get_fact_data_from_stat(common_stat_data: CommonAdvsStatData) -> FactData:
        assert common_stat_data.mean_orders_for_last_days is not None
        assert common_stat_data.all_orders_for_last_days is not None

        pay_for_order: float | None = None
        if common_stat_data.mean_price_for_order is not None:
            pay_for_order = round(common_stat_data.mean_price_for_order, 2)

        return FactData(
            predict_orders=round(
                common_stat_data.mean_orders_for_last_days, 2
            ),
            pay_for_order=pay_for_order,
            original_orders=common_stat_data.all_orders_for_last_days,
            fact_method=common_stat_data.sales_predict_method,
        )

    @staticmethod
    def get_plan_data(adv: AdvSetting) -> PlanData | None:
        plan_orders = adv.plan_for_sales_for_day
        max_pay_for_order: float | None = adv.max_price_for_order
        target_pay_for_order = adv.target_price_for_order
        if any([not plan_orders, not target_pay_for_order, not max_pay_for_order]):
            return None
        try:
            return PlanData(
                orders=plan_orders,
                target_pay_for_order=target_pay_for_order, # noqa
                max_pay_for_order=max_pay_for_order, # noqa
            )
        except Exception as exc:
            logger.exception("Ошибка получения плана")
            raise exc
