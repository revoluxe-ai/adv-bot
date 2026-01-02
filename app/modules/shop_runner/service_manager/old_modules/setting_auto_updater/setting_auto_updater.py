import datetime
import logging
from collections.abc import Awaitable

from sqlalchemy import update

from app.modules.common_advs_stat import CommonAdvsStatData, CommonAdvsStatDataManager

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.utils.db.session_maker import get_async_session_maker as sm

from .plan_fact_change_redis_caches import ChangePlanFact
from .update_adv_setting import update_adv_setting

logger = logging.getLogger(__name__)


class AdvSettingAutoUpdater:
    def __init__(self, adv: AdvSetting, max_last_period: int = 2):
        self._adv = adv
        auto_adv_id = self._adv.adv_id
        self._all_adv_ids = [auto_adv_id]
        auction_id = self._adv.auction_adv_id
        if auction_id:
            self._all_adv_ids.append(auction_id)

        self._max_last_period = max_last_period

    async def __get_stat_data(
        self, keywords: list[CalculatedKeyword]
    ) -> CommonAdvsStatData:
        common_stat_manager = CommonAdvsStatDataManager()
        stat: CommonAdvsStatData = await common_stat_manager.get_data(
            self._adv, keywords, last_days=self._max_last_period
        )
        return stat

    async def get_fact_data_and_stat(
        self, keywords: list[CalculatedKeyword]
    ) -> tuple[FactData, CommonAdvsStatData]:
        stat = await self.__get_stat_data(keywords)
        fact = self._get_fact_data_from_stat(stat)
        return fact, stat

    def _get_fact_data_from_stat(
        self, common_stat_data: CommonAdvsStatData
    ) -> FactData:
        fact_data = self.__get_fact_data_from_stats(common_stat_data)
        return fact_data

    async def get_fact_data(self, keywords: list[CalculatedKeyword]) -> FactData:
        stat = await self.__get_stat_data(keywords)
        fact = self._get_fact_data_from_stat(stat)
        return fact

    async def update(
        self, keywords_coroutine: Awaitable[list[CalculatedKeyword]]
    ) -> None:
        keywords = await keywords_coroutine
        plan = self.get_plan_data(self._adv)
        if not plan:
            return None
        fact = await self.get_fact_data(keywords)
        plan_fact_change = ChangePlanFact(self._adv)
        if await plan_fact_change.check_equal_in_cache(plan, fact):
            return None
        change: bool = await update_adv_setting(self._adv, keywords, plan, fact)
        if change:
            await plan_fact_change.set_new_plan_fact(plan, fact)
        return None

    def __get_fact_data_from_stats(
        self,
        common_stat_data: CommonAdvsStatData,
    ) -> FactData:
        assert common_stat_data.mean_orders_for_last_days is not None
        assert common_stat_data.mean_price_for_order is not None
        assert common_stat_data.all_orders_for_last_days is not None
        mean_orders = round(
            common_stat_data.mean_orders_for_last_days, self._max_last_period
        )
        mean_pay_for_order = round(
            common_stat_data.mean_price_for_order, self._max_last_period
        )
        fact_data = FactData(
            predict_orders=mean_orders,
            pay_for_order=mean_pay_for_order,
            original_orders=common_stat_data.all_orders_for_last_days,
            fact_method=common_stat_data.sales_predict_method,
        )

        return fact_data

    @staticmethod
    def get_plan_data(adv: AdvSetting) -> PlanData | None:
        plan_orders = adv.plan_for_sales_for_day
        max_pay_for_order: float | None = adv.max_price_for_order
        target_pay_for_order = adv.target_price_for_order
        if any([not plan_orders, not target_pay_for_order, not max_pay_for_order]):
            return None
        try:
            plan = PlanData(
                orders=plan_orders,
                target_pay_for_order=target_pay_for_order, # noqa
                max_pay_for_order=max_pay_for_order, # noqa
            )
        except Exception as exc:
            logger.exception('Ошибка получения плана')
            raise exc

        return plan

    @staticmethod
    async def add_top_keyword_to_white_list(keywords: list[CalculatedKeyword]) -> None:
        if not keywords:
            return None
        assert keywords
        keywords.sort(
            key=lambda kw: kw.rating_by_orders, reverse=True
        )  # ignore: type: ignore # predict_ctr не может быть
        # None здесь. Надо переделать CalculatedKeyword, чтобы у него не было полей с None, как минимум для predict_ctr
        first_kw = keywords[0]

        if first_kw.relevant and first_kw.hard_status == 1:
            stmt = (
                update(KeywordSetting)
                .where(KeywordSetting.id == first_kw.keyword_setting_original_id)
                .values({"hard_status": 2})
            )
            async with sm() as session:
                await session.execute(stmt)
                await session.commit()
        return None

    @staticmethod
    def __get_mean_orders(
        stat_data: list[SmallFullAdvStatPerDay],
    ) -> float:
        assert len(stat_data) > 1, "Должно быть данных больше, чем за 2 дня"
        stat_data = stat_data[:2]
        stat_with_views = [stat for stat in stat_data if stat.views > 0]
        today_date = datetime.datetime.now().date()
        stat_data.sort(key=lambda stat: stat.date, reverse=True)
        assert stat_data[0].date == today_date, "первая стата должна быть за сегодня"
        now = datetime.datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_passed_for_last_day = (now - start_of_day).total_seconds() + len(
            stat_with_views
        ) * 24 * 60 * 60
        total_orders_for_last_period = sum([stat.orders for stat in stat_data])

        mean_orders_for_sec = total_orders_for_last_period / seconds_passed_for_last_day

        predict_order_for_day = mean_orders_for_sec * 24 * 60 * 60
        return predict_order_for_day

    @staticmethod
    def __get_mean_pay_for_order(
        stat_data: list[SmallFullAdvStatPerDay],
    ) -> float:
        stat_data.sort(key=lambda st: st.date, reverse=True)
        for n, stat in enumerate(stat_data):
            if stat.orders > 0:
                n += 1
                break
        else:
            n = len(stat_data)
        stat_for_analyze = stat_data[:n]

        sum_orders = sum([stat.orders for stat in stat_for_analyze])
        if sum_orders == 0:
            sum_orders = 1
        sum_spend = sum([stat.spend for stat in stat_for_analyze])
        return sum_spend / sum_orders
