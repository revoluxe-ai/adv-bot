from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager
from app.modules.shop_runner.wb_statistic_manager.backend.types.common_card_stat import CommonCardStat
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker


@dataclass
class CommonAdvsStatData:
    """Класс для хранения данных о ключевых словах рекламной кампании"""

    adv_setting: AdvSetting
    keywords: list[CalculatedKeyword]
    min_ctr: float
    auto_cpm: int
    auction_cpm: int | None
    total_spend: float
    addition_spend_in_adv: float
    all_orders_for_last_days: int | None
    mean_orders_for_last_days: float | None
    mean_price_for_order: float | None
    spend_for_inner_advs: float | None
    full_adv_stat_for_last_days_for_auto_adv: SmallFullAdvStat
    full_adv_stat_for_last_days_for_auction: SmallFullAdvStat
    common_stat: CommonCardStat | None


class CommonAdvsStatDataManager:
    """Менеджер для получения данных о ключевых словах рекламной кампании"""

    @staticmethod
    async def get_data(
        adv_setting: AdvSetting, keywords: list[CalculatedKeyword], last_days: int
    ) -> CommonAdvsStatData:
        """Получает все необходимые данные для отображения информации о ключевых словах"""

        # Получаем min_ctr
        min_ctr = await data_manager.get_min_ctr(adv_setting)

        # Получаем CPM для аукциона
        auction_cpm = None
        if search_adv_id := adv_setting.search_adv_id:
            stmt = select(AdvSetting.cpm).where(AdvSetting.adv_id == search_adv_id)
            async with _sm() as session:
                result = await session.execute(stmt)
                auction_cpm = result.scalar_one_or_none()

        pass_days = last_days - 1
        end_date = datetime.now()
        start_date = end_date - timedelta(days=pass_days)

        # Статистика для авто-рекламы
        full_adv_stat_for_last_days_for_auto_adv = await full_wb_adv_stat.get_stats_by_last_days(
            [adv_setting.adv_id], start_date, end_date
        )

        # Статистика для аукциона
        full_adv_stat_for_last_days_for_auction = await full_wb_adv_stat.get_stats_by_last_days(
            [adv_setting.search_adv_id], start_date, end_date
        )

        # Общий расход
        full_spend_for_all_advs = (
            full_adv_stat_for_last_days_for_auto_adv.spend + full_adv_stat_for_last_days_for_auction.spend
        )

        # Общая статистика
        common_stat: CommonCardStat | None = await common_stat_manager.get_stats_for_last_period(
            int(adv_setting.nmids[0]), pass_days
        )

        # Рассчитываем дополнительные метрики
        base_common_orders = None
        all_orders_from_advs = (
            full_adv_stat_for_last_days_for_auto_adv.orders + full_adv_stat_for_last_days_for_auction.orders
        )
        mean_orders_for_days = None
        mean_price_for_order = None
        spend_for_inner_advs_for_days = None

        if common_stat:
            base_common_orders = common_stat.orders
            if base_common_orders < all_orders_from_advs:
                base_common_orders = all_orders_from_advs
            if base_common_orders == 0:
                base_common_orders = 1
            spend_for_inner_advs_for_days = full_spend_for_all_advs

            now = datetime.now()
            hours_passed = now.hour + now.minute / 60 + now.second / 3600
            fraction_of_day = hours_passed / 24 + pass_days

            mean_orders_for_days = base_common_orders / fraction_of_day
            mean_price_for_order = spend_for_inner_advs_for_days / base_common_orders

        # Получаем расходы на ключевые слова
        spend_for_keywords_in_auto_adv = await full_wb_adv_stat.get_keywords_spend(
            [adv_setting.adv_id], start_date, end_date, "advkeyword"
        )

        addition_spend_in_adv = full_adv_stat_for_last_days_for_auto_adv.spend - spend_for_keywords_in_auto_adv

        return CommonAdvsStatData(
            adv_setting=adv_setting,
            keywords=keywords,
            min_ctr=min_ctr,
            auto_cpm=adv_setting.cpm,
            auction_cpm=auction_cpm,
            total_spend=full_spend_for_all_advs,
            addition_spend_in_adv=addition_spend_in_adv,
            all_orders_for_last_days=base_common_orders,
            mean_orders_for_last_days=mean_orders_for_days,
            mean_price_for_order=mean_price_for_order,
            spend_for_inner_advs=spend_for_inner_advs_for_days,
            full_adv_stat_for_last_days_for_auto_adv=full_adv_stat_for_last_days_for_auto_adv,
            full_adv_stat_for_last_days_for_auction=full_adv_stat_for_last_days_for_auction,
            common_stat=common_stat,
        )
