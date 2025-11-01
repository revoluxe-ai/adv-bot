from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting

if TYPE_CHECKING:
    from .max_cpm_redis_status_manager import MaxCpmRedisStatusManager
    from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
        PlanData,
        FactData,
    )


class AutoMaxBidManager:

    def __init__(self, max_cpm_status_manager: "MaxCpmRedisStatusManager") -> None:
        self._max_cpm_status_manager = max_cpm_status_manager

    async def get_max_cpm(
        self,
        adv: AdvSetting,
        keywords: list[CalculatedKeyword],
        user_max_cpm: int | None,
        period_days: int = 2,
    ) -> int:
        max_cpm = await self._get_max_cpm(adv, keywords, period_days)
        if user_max_cpm is None:
            if max_cpm is None:
                # Нет пользовательского лимита и не удалось рассчитать — используем безопасное значение
                result_max_cpm = 0
            else:
                result_max_cpm = int(max_cpm)
        else:
            if max_cpm is None:
                result_max_cpm = user_max_cpm
            else:
                result_max_cpm = min(int(max_cpm), user_max_cpm)
        await self._max_cpm_status_manager.set(adv, result_max_cpm)
        return result_max_cpm

    async def _get_max_cpm(
        self, adv: AdvSetting, keywords: list[CalculatedKeyword], period_days: int
    ) -> float | None:
        pay_for_order = await self._get_target_pay_for_order(adv, keywords)
        if not pay_for_order:
            return None
        ratio_views_to_clicks_for_active_keywords = self._get_ratio_for_active_keywords(
            keywords
        )
        clicks_to_orders_ratio = await self._get_clicks_to_orders_ratio_for_keywords(
            adv, period_days
        )
        if not clicks_to_orders_ratio:
            return None
        return self.__get_max_cpm(
            pay_for_order,
            ratio_views_to_clicks_for_active_keywords,
            clicks_to_orders_ratio,
        )

    @staticmethod
    def __get_max_cpm(
        pay_for_order: float, ratio_views_to_clicks: float, clicks_to_orders_ratio: float
    ) -> float:
        views_for_order = ratio_views_to_clicks * clicks_to_orders_ratio
        max_pay_for_view = pay_for_order / views_for_order
        max_cpm = max_pay_for_view * 1000
        return max_cpm

    async def _get_clicks_to_orders_ratio_for_keywords(
        self, adv: AdvSetting, period_days: int
    ) -> float | None:
        from . import clickhouse_manager

        # TODO: тут логика завязана на 1 артикул в РК
        # Смотрим только по одной РК, чтобы точно узнать конверсию из показов ключей в заказы
        # TODO: Ошибка в проде: смотрели Автокампанию для определения конверсии в ключах
        adv_ids = [
            adv.search_adv_id,
        ]
        clicks_to_order_ratio: float = (
            await clickhouse_manager.get_clicks_to_orders_ration_on_phrases(
                adv_ids, period_days
            )
        )
        return clicks_to_order_ratio

    async def _get_target_pay_for_order(
        self, adv: AdvSetting, keywords: list[CalculatedKeyword]
    ) -> float | None:
        from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater import (
            AdvSettingAutoUpdater as PlanFactGetter,
        )

        plan_fact_getter = PlanFactGetter(adv, 2)
        plan_data: PlanData = plan_fact_getter.get_plan_data(adv)
        if not plan_data.full_settings:
            return None
        fact_data: FactData = await plan_fact_getter.get_fact_data(keywords)
        if fact_data.predict_orders < plan_data.orders:
            return plan_data.max_pay_for_order
        else:
            return plan_data.target_pay_for_order

    @staticmethod
    def _get_ratio_for_active_keywords(keywords: list[CalculatedKeyword]) -> float:
        views = 0
        clicks = 0
        for keyword in keywords:
            if keyword.status == "good":
                views += keyword.views or 0
                clicks += keyword.clicks or 0
        # TODO: Тут подумать над дефолтными показами
        if clicks == 0:
            clicks = 1
        if views == 0:
            views = 100
        return views / clicks
