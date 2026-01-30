from __future__ import annotations

import logging

from app.modules.common_advs_stat import CommonAdvsStatData, CommonAdvsStatDataManager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

logger = logging.getLogger(__name__)


class PlanFactProvider:
    def __init__(self, adv: AdvSetting, max_last_period: int = 2):
        self._adv = adv
        self._max_last_period = max_last_period

    async def get_fact_data_and_stat(
        self, keywords: list[CalculatedKeyword]
    ) -> tuple[FactData, CommonAdvsStatData]:
        stat = await self._get_stat_data(keywords)
        return self._get_fact_data_from_stat(stat), stat

    async def get_fact_data(self, keywords: list[CalculatedKeyword]) -> FactData:
        stat = await self._get_stat_data(keywords)
        return self._get_fact_data_from_stat(stat)

    async def _get_stat_data(
        self, keywords: list[CalculatedKeyword]
    ) -> CommonAdvsStatData:
        common_stat_manager = CommonAdvsStatDataManager()
        return await common_stat_manager.get_data(
            self._adv, keywords, last_days=self._max_last_period
        )

    def _get_fact_data_from_stat(self, common_stat_data: CommonAdvsStatData) -> FactData:
        assert common_stat_data.mean_orders_for_last_days is not None
        assert common_stat_data.mean_price_for_order is not None
        assert common_stat_data.all_orders_for_last_days is not None

        return FactData(
            predict_orders=round(
                common_stat_data.mean_orders_for_last_days, 2
            ),
            pay_for_order=round(
                common_stat_data.mean_price_for_order, 2
            ),
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
                target_pay_for_order=target_pay_for_order,
                max_pay_for_order=max_pay_for_order,
            )
        except Exception as exc:
            logger.exception("Ошибка получения плана")
            raise exc
