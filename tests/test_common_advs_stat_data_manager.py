import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from app.modules.common_advs_stat.data_manager import CommonAdvsStatData, CommonAdvsStatDataManager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.data_classes.adv import AdvType
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat, DayStats, BoosterStats
import math
import numpy as np
from contextlib import asynccontextmanager

# Расширяем класс FullAdvStat для тестов, чтобы у него было свойство spend
class TestFullAdvStat(FullAdvStat):
    @property
    def spend(self):
        return self.sum

    @property
    def avg_position(self):
        return 2.5

# Переопределяем AdvSetting для тестов
class TestAdvSetting(AdvSetting):
    @property
    def search_adv_id(self):
        return self._search_adv_id

@pytest.fixture
def mock_adv_setting():
    mock_adv_setting = MagicMock()
    mock_adv_setting.id = 12
    mock_adv_setting.name = "test_adv"
    mock_adv_setting.type = 8  # Автоматическая реклама (auto)
    mock_adv_setting.search_adv_id = 12345
    mock_adv_setting.cpm = 200
    return mock_adv_setting

@pytest.fixture
def mock_keywords():
    return [MagicMock() for _ in range(5)]

@pytest.fixture
def mock_full_adv_stat():
    stat = MagicMock()
    stat.spend = 1000
    stat.avg_position = 2.5
    return stat

@pytest.mark.asyncio
async def test_get_data():
    # Создаем моки для всех необходимых функций
    mock_get_min_ctr = AsyncMock()
    mock_get_min_ctr.return_value = 0.5
    
    mock_get_keywords_spend = AsyncMock()
    # Определяем разные возвращаемые значения в зависимости от аргументов
    async def side_effect_get_keywords_spend(adv_ids, *args, **kwargs):
        if adv_ids == ["test_adv_id"]:  # Для auto рекламы
            return 100.0
        elif adv_ids == ["test_search_adv_id"]:  # Для search рекламы (аукцион)
            return 100.0
        return 0.0
    
    mock_get_keywords_spend.side_effect = side_effect_get_keywords_spend
    
    mock_get_stats_by_last_days = AsyncMock()
    # Определяем разные возвращаемые значения в зависимости от аргументов
    async def side_effect_get_stats(adv_ids, *args, **kwargs):
        if adv_ids == ["test_adv_id"]:  # Для auto рекламы
            return TestFullAdvStat(
                dates=["2024-03-20", "2024-03-21", "2024-03-22"],
                views=1000,
                clicks=100,
                ctr=10.0,
                cpc=1.0,
                sum=100.0,
                atbs=50,
                orders=10,
                cr=10.0,
                shks=20,
                sum_price=2000.0,
                days=[],
                advertId=123
            )
        elif adv_ids == ["test_search_adv_id"]:  # Для search рекламы (аукцион)
            return TestFullAdvStat(
                dates=["2024-03-20", "2024-03-21", "2024-03-22"],
                views=1000,
                clicks=100,
                ctr=10.0,
                cpc=1.0,
                sum=100.0,
                atbs=50,
                orders=10,
                cr=10.0,
                shks=20,
                sum_price=2000.0,
                days=[],
                advertId=456
            )
        return None
    
    mock_get_stats_by_last_days.side_effect = side_effect_get_stats
    
    mock_get_stats_for_last_period = AsyncMock()
    mock_get_stats_for_last_period.return_value = TestFullAdvStat(
        dates=["2024-03-20", "2024-03-21", "2024-03-22"],
        views=2000,
        clicks=200,
        ctr=10.0,
        cpc=1.0,
        sum=200.0,
        atbs=100,
        orders=20,
        cr=10.0,
        shks=40,
        sum_price=4000.0,
        days=[],
        advertId=123
    )
    
    # Создаем мок для сессии
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 200.0
    mock_session.execute.return_value = mock_result
    
    # Создаем асинхронный контекстный менеджер
    class AsyncContextManager:
        async def __aenter__(self):
            return mock_session
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    mock_async_session_cm = AsyncContextManager()
    
    # Патчим все необходимые функции
    with patch('app.modules.wb_adv_updater.data_manager.get_min_ctr', mock_get_min_ctr), \
         patch('app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.get_keywords_spend', mock_get_keywords_spend), \
         patch('app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.get_stats_by_last_days', mock_get_stats_by_last_days), \
         patch('app.modules.shop_runner.wb_statistic_manager.backend.common_stat_manager.get_stats_for_last_period', mock_get_stats_for_last_period), \
         patch('app.modules.common_advs_stat.data_manager._sm', return_value=mock_async_session_cm):
        
        # Создаем тестовые данные
        adv_setting = TestAdvSetting(
            id=1,
            adv_id="test_adv_id",
            name="Test Adv",
            wb_cabinet_id=1,
            active_status=True,
            bot_active=True,
            nmids=[12345, 67890],
            pass_days=0,
            type="search",
            _search_adv_id="test_search_adv_id"
        )
        
        keywords = [
            CalculatedKeyword(
                text="test1",
                views=100,
                clicks=10,
                spend=50.0,
                status=0
            ),
            CalculatedKeyword(
                text="test2",
                views=200,
                clicks=20,
                spend=100.0,
                status=0
            )
        ]
        
        # Вызываем тестируемый метод
        result = await CommonAdvsStatDataManager.get_data(adv_setting, keywords)
        
        # Проверяем, что все моки были вызваны
        mock_get_min_ctr.assert_called_once()
        mock_get_keywords_spend.assert_called()
        mock_get_stats_by_last_days.assert_called()
        mock_get_stats_for_last_period.assert_called_once()
        mock_session.execute.assert_called_once()
        
        # Проверяем результаты
        assert result.min_ctr == 0.5
        assert result.auction_cpm == 200.0
        assert result.total_spend == 200.0  # 100.0 (auto) + 100.0 (auction)
        assert result.addition_spend_in_adv == 0.0  # 100.0 - 100.0
        assert result.all_orders_for_last_3_days == 20
        assert result.mean_orders_for_3_days is not None
        assert result.mean_price_for_order is not None
        assert result.spend_for_inner_adv_for_3_days == 200.0
        assert isinstance(result.full_adv_stat_for_last_3_days_for_auto_adv, FullAdvStat)
        assert isinstance(result.full_adv_stat_for_last_3_days_for_auction, FullAdvStat)
        assert isinstance(result.common_stat, FullAdvStat)

def test_calculate_vector_distance():
    # Создаем тестовый объект CommonAdvsStatData
    data = CommonAdvsStatData(
        adv_setting=MagicMock(),
        keywords=[],
        min_ctr=0.01,
        auto_cpm=100,
        auction_cpm=200,
        total_spend=1000,
        addition_spend_in_adv=200,
        all_orders_for_last_3_days=30,
        mean_orders_for_3_days=10,
        mean_price_for_order=50,
        spend_for_inner_adv_for_3_days=1000,
        full_adv_stat_for_last_3_days_for_auto_adv=MagicMock(),
        full_adv_stat_for_last_3_days_for_auction=MagicMock(),
        common_stat=MagicMock(),
        plan_vector={
            "position": 1,
            "orders": 10,
            "cpo": 50
        },
        fact_vector={
            "position": 2,  # Хуже плана (выше числом - хуже)
            "orders": 5,    # Хуже плана (меньше - хуже)
            "cpo": 100      # Хуже плана (больше - хуже)
        }
    )
    
    # Проверяем расчет расстояния с равными весами
    distance = data.calculate_vector_distance()
    assert distance > 0
    
    # Проверяем расчет расстояния с пользовательскими весами
    custom_weights = {
        "position": 2.0,  # Позиция важнее
        "orders": 1.0,
        "cpo": 0.5       # CPO менее важен
    }
    
    custom_distance = data.calculate_vector_distance(weights=custom_weights)
    assert custom_distance > 0
    
    # Создаем данные, где все показатели соответствуют плану
    perfect_data = CommonAdvsStatData(
        adv_setting=MagicMock(),
        keywords=[],
        min_ctr=0.01,
        auto_cpm=100,
        auction_cpm=200,
        total_spend=1000,
        addition_spend_in_adv=200,
        all_orders_for_last_3_days=30,
        mean_orders_for_3_days=10,
        mean_price_for_order=50,
        spend_for_inner_adv_for_3_days=1000,
        full_adv_stat_for_last_3_days_for_auto_adv=MagicMock(),
        full_adv_stat_for_last_3_days_for_auction=MagicMock(),
        common_stat=MagicMock(),
        plan_vector={
            "position": 1,
            "orders": 10,
            "cpo": 50
        },
        fact_vector={
            "position": 1,  # Соответствует плану
            "orders": 10,   # Соответствует плану
            "cpo": 50       # Соответствует плану
        }
    )
    
    # Расстояние для идеального случая должно быть близко к нулю
    perfect_distance = perfect_data.calculate_vector_distance()
    assert perfect_distance == 0

def test_get_campaign_efficiency_score():
    # Создаем данные с разными уровнями соответствия плану
    perfect_data = CommonAdvsStatData(
        adv_setting=MagicMock(),
        keywords=[],
        min_ctr=0.01,
        auto_cpm=100,
        auction_cpm=200,
        total_spend=1000,
        addition_spend_in_adv=200,
        all_orders_for_last_3_days=30,
        mean_orders_for_3_days=10,
        mean_price_for_order=50,
        spend_for_inner_adv_for_3_days=1000,
        full_adv_stat_for_last_3_days_for_auto_adv=MagicMock(),
        full_adv_stat_for_last_3_days_for_auction=MagicMock(),
        common_stat=MagicMock(),
        plan_vector={"position": 1, "orders": 10, "cpo": 50},
        fact_vector={"position": 1, "orders": 10, "cpo": 50}  # Идеальное соответствие
    )
    
    # Проверяем идеальный случай (100%)
    perfect_score = perfect_data.get_campaign_efficiency_score()
    assert perfect_score == 100
    
    # Создаем данные с плохими показателями
    bad_data = CommonAdvsStatData(
        adv_setting=MagicMock(),
        keywords=[],
        min_ctr=0.01,
        auto_cpm=100,
        auction_cpm=200,
        total_spend=1000,
        addition_spend_in_adv=200,
        all_orders_for_last_3_days=30,
        mean_orders_for_3_days=10,
        mean_price_for_order=50,
        spend_for_inner_adv_for_3_days=1000,
        full_adv_stat_for_last_3_days_for_auto_adv=MagicMock(),
        full_adv_stat_for_last_3_days_for_auction=MagicMock(),
        common_stat=MagicMock(),
        plan_vector={"position": 1, "orders": 10, "cpo": 50},
        fact_vector={"position": 10, "orders": 1, "cpo": 500}  # Серьезные отклонения
    )
    
    # Проверяем плохой случай (низкая оценка)
    bad_score = bad_data.get_campaign_efficiency_score()
    assert bad_score < 30  # Ожидаем очень низкую оценку
    
    # Создаем данные с частичным соответствием
    partial_data = CommonAdvsStatData(
        adv_setting=MagicMock(),
        keywords=[],
        min_ctr=0.01,
        auto_cpm=100,
        auction_cpm=200,
        total_spend=1000,
        addition_spend_in_adv=200,
        all_orders_for_last_3_days=30,
        mean_orders_for_3_days=10,
        mean_price_for_order=50,
        spend_for_inner_adv_for_3_days=1000,
        full_adv_stat_for_last_3_days_for_auto_adv=MagicMock(),
        full_adv_stat_for_last_3_days_for_auction=MagicMock(),
        common_stat=MagicMock(),
        plan_vector={"position": 1, "orders": 10, "cpo": 50},
        fact_vector={"position": 2, "orders": 8, "cpo": 60}  # Небольшие отклонения
    )
    
    # Проверяем частичное соответствие (средняя оценка)
    partial_score = partial_data.get_campaign_efficiency_score()
    assert 30 < partial_score < 90  # Ожидаем среднюю оценку 