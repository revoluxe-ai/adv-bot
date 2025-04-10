from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.full_stat_adv_updater.types import FullAdvStat
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager
from app.utils.db.session_maker import get_async_session_maker
from app.modules.wb_adv_updater import data_manager
import math

_sm = get_async_session_maker


@dataclass
class CommonAdvsStatData:
    """Класс для хранения данных о ключевых словах рекламной кампании"""
    adv_setting: AdvSetting
    keywords: List[CalculatedKeyword]
    min_ctr: float
    auto_cpm: int
    auction_cpm: Optional[int]
    total_spend: float
    addition_spend_in_adv: float
    all_orders_for_last_3_days: Optional[int]
    mean_orders_for_3_days: Optional[float]
    mean_price_for_order: Optional[float]
    spend_for_inner_adv_for_3_days: Optional[float]
    full_adv_stat_for_last_3_days_for_auto_adv: SmallFullAdvStat
    full_adv_stat_for_last_3_days_for_auction: SmallFullAdvStat
    common_stat: Optional[FullAdvStat]


class CommonAdvsStatDataManager:
    """Менеджер для получения данных о ключевых словах рекламной кампании"""
    
    @classmethod
    async def get_data(cls, adv_setting: AdvSetting, keywords: List[CalculatedKeyword]) -> CommonAdvsStatData:
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
        
        # Получаем статистику за последние 3 дня
        pass_days = 2
        end_date = datetime.now()
        start_date = end_date - timedelta(days=pass_days)
        
        # Статистика для авто-рекламы
        full_adv_stat_for_last_3_days_for_auto_adv = await full_wb_adv_stat.get_stats_by_last_days(
            [adv_setting.adv_id],
            start_date,
            end_date
        )
        
        # Статистика для аукциона
        full_adv_stat_for_last_3_days_for_auction = await full_wb_adv_stat.get_stats_by_last_days(
            [adv_setting.search_adv_id],
            start_date,
            end_date
        )
        
        # Общий расход
        full_spend_for_all_advs = (
            full_adv_stat_for_last_3_days_for_auto_adv.spend +
            full_adv_stat_for_last_3_days_for_auction.spend
        )
        
        # Общая статистика
        common_stat = await common_stat_manager.get_stats_for_last_period(adv_setting.nmids[0], pass_days)
        
        # Рассчитываем дополнительные метрики
        all_orders_for_last_3_days = None
        mean_orders_for_3_days = None
        mean_price_for_order = None
        spend_for_inner_adv_for_3_days = None
        
        if common_stat:
            all_orders_for_last_3_days = common_stat.orders
            spend_for_inner_adv_for_3_days = full_spend_for_all_advs
            
            now = datetime.now()
            hours_passed = now.hour + now.minute / 60 + now.second / 3600
            fraction_of_day = hours_passed / 24 + pass_days
            
            mean_orders_for_3_days = all_orders_for_last_3_days / fraction_of_day
            mean_price_for_order = spend_for_inner_adv_for_3_days / common_stat.orders if common_stat.orders else 0
        
        # Получаем расходы на ключевые слова
        spend_for_keywords_in_auto_adv = await full_wb_adv_stat.get_keywords_spend(
            [adv_setting.adv_id],
            start_date,
            end_date,
            'advkeyword_new'
        )

        addition_spend_in_adv = full_adv_stat_for_last_3_days_for_auto_adv.spend - spend_for_keywords_in_auto_adv

        return CommonAdvsStatData(
            adv_setting=adv_setting,
            keywords=keywords,
            min_ctr=min_ctr,
            auto_cpm=adv_setting.cpm,
            auction_cpm=auction_cpm,
            total_spend=full_spend_for_all_advs,
            addition_spend_in_adv=addition_spend_in_adv,
            all_orders_for_last_3_days=all_orders_for_last_3_days,
            mean_orders_for_3_days=mean_orders_for_3_days,
            mean_price_for_order=mean_price_for_order,
            spend_for_inner_adv_for_3_days=spend_for_inner_adv_for_3_days,
            full_adv_stat_for_last_3_days_for_auto_adv=full_adv_stat_for_last_3_days_for_auto_adv,
            full_adv_stat_for_last_3_days_for_auction=full_adv_stat_for_last_3_days_for_auction,
            common_stat=common_stat
        )
