from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater \
    import AdvSettingAutoUpdater as PlanFactGetter
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import PlanData, FactData


class AutoMaxBidManager:

    def __init__(self, adv: AdvSetting,
                 keywords: list[CalculatedKeyword],
                 user_max_cpm: int,
                 period_days: int = 7,
                 ) -> None:
        self._adv = adv
        self._keywords = keywords
        self._period_days = period_days
        self._user_max_cpm = user_max_cpm

    async def get_max_cpm(self) -> int:
        max_cpm = await self._get_max_cpm()
        user_max_cpm = self._user_max_cpm
        if max_cpm is None:
            return user_max_cpm
        else:
            max_cpm = min(int(max_cpm), user_max_cpm)
            return max_cpm

    async def _get_max_cpm(self) -> float | None:
        pay_for_order = await self._get_target_pay_for_order()
        if not pay_for_order:
            return None
        ratio_views_to_clicks_for_active_keywords = self._get_ratio_for_active_keywords(self._keywords)
        clicks_to_orders_ratio = await self._get_clicks_to_orders_ratio()
        return self.__get_max_cpm(pay_for_order, ratio_views_to_clicks_for_active_keywords, clicks_to_orders_ratio)

    @staticmethod
    def __get_max_cpm(
            pay_for_order: float,
            ratio_views_to_clicks: float,
            clicks_to_orders_ratio) -> float:
        views_for_order = ratio_views_to_clicks * clicks_to_orders_ratio
        max_pay_for_view = pay_for_order / views_for_order
        max_cpm = max_pay_for_view * 1000
        return max_cpm

    async def _get_clicks_to_orders_ratio(self) -> float | None:
        from . import clickhouse_manager
        # TODO: тут логика завязана на 1 артикул в РК
        adv_ids = [
            self._adv.adv_id,
            self._adv.search_adv_id
        ]
        clicks_to_order_ratio: float = await (clickhouse_manager.
                                              get_clicks_to_orders_ration_on_phrases(adv_ids,
                                                                                     self._period_days))
        return clicks_to_order_ratio

    async def _get_target_pay_for_order(self) -> float | None:
        plan_fact_getter = PlanFactGetter(self._adv, 2)
        plan_data: PlanData = plan_fact_getter.get_plan_data(self._adv)
        if not plan_data.full_settings:
            return None
        fact_data: FactData = await plan_fact_getter.get_fact_data(self._keywords)
        if fact_data.predict_orders < plan_data.orders:
            return plan_data.max_pay_for_order
        else:
            return plan_data.target_pay_for_order

    @staticmethod
    def _get_ratio_for_active_keywords(keywords: list[CalculatedKeyword]) -> float:
        views = 0
        clicks = 0
        for keyword in keywords:
            if keyword.status == 'good':
                views += keyword.views or 0
                clicks += keyword.clicks or 0
        if clicks == 0:
            clicks = 1
        return views / clicks
