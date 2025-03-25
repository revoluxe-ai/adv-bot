from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Union
from sqlalchemy import select
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.full_stat_adv_updater.types import FullAdvStat
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager
from app.utils.db.session_maker import get_async_session_maker
from app.modules.wb_adv_updater import data_manager
import math

_sm = get_async_session_maker

# Добавляем свойство diff_to_plan в AdvSetting
# Создаем приватный атрибут
setattr(AdvSetting, '_diff_to_plan', None)

# Создаем свойство и сеттер
def get_diff_to_plan(self) -> Optional[float]:
    """Возвращает разницу между фактическими и плановыми показателями"""
    return self._diff_to_plan

def set_diff_to_plan(self, value: float):
    """Устанавливает разницу между фактическими и плановыми показателями"""
    if value is not None and not isinstance(value, float):
        raise ValueError("diff_to_plan должно быть числом с плавающей точкой или None")
    self._diff_to_plan = value

# Устанавливаем свойство diff_to_plan
setattr(AdvSetting, 'diff_to_plan', property(get_diff_to_plan, set_diff_to_plan))

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
    full_adv_stat_for_last_3_days_for_auto_adv: FullAdvStat
    full_adv_stat_for_last_3_days_for_auction: FullAdvStat
    common_stat: Optional[FullAdvStat]
    # Векторы плана и факта
    plan_vector: dict
    fact_vector: dict
    
    def calculate_vector_distance(self) -> float:
        """
        Рассчитывает нормализованное расстояние между вектором плана и фактом
        
        Returns:
            float: Нормализованное расстояние между векторами (чем меньше, тем лучше)
        """
        plan_orders = self.plan_vector.get("orders", 0)
        fact_orders = self.fact_vector.get("orders", 0)
        
        # Если fact_orders равен None, сразу возвращаем расстояние 1.0
        if fact_orders is None:
            return 1.0
            
        # Если нет данных о заказах, возвращаем максимальное отклонение
        if plan_orders == 0:
            return 2.0
            
        # Рассчитываем отклонение заказов
        orders_diff = 0
        if fact_orders < plan_orders:
            # Если заказов меньше плана, считаем отклонение
            orders_diff = (plan_orders - fact_orders) / plan_orders
            
        # Если отклонение заказов большое (больше 50%), устанавливаем высокий приоритет
        if orders_diff > 0.5:
            return 1.5
            
        # Если заказов достаточно (отклонение меньше 50%), проверяем себестоимость
        plan_cpo = self.plan_vector.get("cpo", 0)
        fact_cpo = self.fact_vector.get("cpo", 0)
        
        # Если fact_cpo равен None, сразу возвращаем расстояние 1.0
        if fact_cpo is None:
            return 1.0
            
        if plan_cpo == 0:
            return 1.0
            
        # Нормализуем отклонение себестоимости
        cpo_diff = (fact_cpo - plan_cpo) / plan_cpo if fact_cpo > plan_cpo else 0
        
        # Возвращаем нормализованное отклонение (0 - идеально, 1 - максимальное отклонение)
        return min(1.0, max(orders_diff, cpo_diff))
    
    def get_campaign_efficiency_score(self) -> float:
        """
        Возвращает оценку эффективности кампании от 0 до 100
        чем ближе к 100, тем лучше кампания соответствует плану
        
        Returns:
            float: Оценка от 0 до 100
        """
        distance = self.calculate_vector_distance()
        # Преобразуем расстояние в оценку (чем меньше расстояние, тем выше оценка)
        # Используем экспоненциальное затухание для перевода расстояния в оценку
        score = 100 * math.exp(-2 * distance)
        return max(0, min(100, score))  # Ограничиваем значение от 0 до 100

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
                auction_cpm = result.scalar_one()
        
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
        
        spend_for_keywords_in_auction_adv = await full_wb_adv_stat.get_keywords_spend(
            [adv_setting.search_adv_id],
            start_date,
            end_date,
            'advkeyword_new'
        )
        
        spend_for_keywords = spend_for_keywords_in_auto_adv + spend_for_keywords_in_auction_adv
        addition_spend_in_adv = full_adv_stat_for_last_3_days_for_auto_adv.spend - spend_for_keywords_in_auto_adv
        
        # Создаем векторы плана и факта
        # Получаем плановые значения из настроек кампании или используем дефолтные
        # Планируемое количество заказов (из настроек или план карточки)
        target_orders_per_day = getattr(adv_setting, 'target_orders_per_day', 10)
        
        # Плановая себестоимость заказа (руб.)
        target_cpo = getattr(adv_setting, 'target_cpo', 100)
        
        plan_vector = {
            "orders": target_orders_per_day,
            "cpo": target_cpo
        }
        
        # Фактические значения
        fact_vector = {
            "orders": mean_orders_for_3_days,
            "cpo": mean_price_for_order
        }
        
        text = f"Ключевых фраз: {len(keywords)}"
        call = "keywords"
        
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
            common_stat=common_stat,
            plan_vector=plan_vector,
            fact_vector=fact_vector
        )
        
    @classmethod
    async def calculate_diff_to_plan_for_adv_settings(
        self,
            adv_settings: List[AdvSetting],
            common_stat: CommonAdvsStatData,
            full_adv_stat_for_auto_adv: FullAdvStat
    ) -> List[AdvSetting]:
        """Рассчитывает отклонение от плана для списка настроек рекламы"""
        if not common_stat:
            for adv_setting in adv_settings:
                # Для полностью отсутствующих данных - максимальное отклонение
                adv_setting.diff_to_plan = 2.0
            return adv_settings

        # Получаем плановые значения
        plan_orders = common_stat.plan_vector.get("orders", 0)
        plan_cpo = common_stat.plan_vector.get("cpo", 0)

        for adv_setting in adv_settings:
            # Фактические значения для данной рекламной кампании
            fact_orders = common_stat.mean_orders_for_3_days
            fact_cpo = common_stat.mean_price_for_order
            
            # Если fact_orders равен None, устанавливаем расстояние 1.0 и переходим к следующей кампании
            if fact_orders is None:
                adv_setting.diff_to_plan = 1.0
                continue
                
            # Если нет данных о заказах, максимальное отклонение
            if plan_orders == 0:
                adv_setting.diff_to_plan = 2.0
                continue
                
            # Рассчитываем отклонение заказов
            orders_diff = 0
            if fact_orders < plan_orders:
                # Если заказов меньше плана, считаем отклонение
                orders_diff = (plan_orders - fact_orders) / plan_orders
                
            # Если отклонение заказов большое (больше 50%), устанавливаем высокий приоритет
            if orders_diff > 0.5:
                adv_setting.diff_to_plan = 1.5
                continue
                
            # Если fact_cpo равен None, устанавливаем расстояние 1.0 и переходим к следующей кампании
            if fact_cpo is None:
                adv_setting.diff_to_plan = 1.0
                continue
                
            # Если заказов достаточно (отклонение меньше 50%), проверяем себестоимость
            if plan_cpo == 0:
                adv_setting.diff_to_plan = 1.0
                continue
                
            # Нормализуем отклонение себестоимости
            cpo_diff = (fact_cpo - plan_cpo) / plan_cpo if fact_cpo > plan_cpo else 0
            
            # Устанавливаем нормализованное отклонение (0 - идеально, 1 - максимальное отклонение)
            adv_setting.diff_to_plan = min(1.0, max(orders_diff, cpo_diff))

        return adv_settings 