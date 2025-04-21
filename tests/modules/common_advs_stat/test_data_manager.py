import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from app.modules.common_advs_stat.data_manager import CommonAdvsStatData, CommonAdvsStatDataManager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.data_classes.adv import AdvType
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat, DayStats, BoosterStats, SmallFullAdvStat
from app.modules.shop_runner.wb_statistic_manager.backend.types.common_card_stat import CommonCardStat
import math
import numpy as np
from contextlib import asynccontextmanager

# Создаем функцию для создания экземпляра FullAdvStat с дополнительными свойствами
@pytest.fixture
def create_test_full_adv_stat():
    def _create_test_full_adv_stat(**kwargs):
        # Сначала создаем FullAdvStat со всеми необходимыми параметрами
        full_adv_stat = FullAdvStat(**kwargs)
        # Затем создаем SmallFullAdvStat с нужными полями
        return SmallFullAdvStat(
            views=full_adv_stat.views,
            clicks=full_adv_stat.clicks,
            spend=full_adv_stat.sum,  # Используем sum как spend
            added_to_cart=full_adv_stat.atbs,
            orders=full_adv_stat.orders,
            sum_price=full_adv_stat.sum_price
        )
    return _create_test_full_adv_stat

@pytest.mark.asyncio
async def test_get_data(create_test_full_adv_stat):
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
            return create_test_full_adv_stat(
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
            return create_test_full_adv_stat(
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
    mock_get_stats_for_last_period.return_value = CommonCardStat(
        nmid=12345,
        open_card=2000,
        add_to_cart=100,
        orders=20,
        orders_sum=4000.0,
        buy_outs=15
    )
    
    # Создаем мок для сессии
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 300.0
    mock_session.execute.return_value = mock_result
    
    # Создаем асинхронный контекстный менеджер
    class AsyncContextManager:
        async def __aenter__(self):
            return mock_session
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    mock_async_session_cm = AsyncContextManager()
    
    # Создаем тестовые данные
    adv_setting = MagicMock()
    adv_setting.id = 1
    adv_setting.adv_id = "test_adv_id"
    adv_setting.name = "Test Adv"
    adv_setting.wb_cabinet_id = 1
    adv_setting.active_status = True
    adv_setting.bot_active = True
    adv_setting.nmids = [12345, 67890]
    adv_setting.pass_days = 0
    adv_setting.type = "search"
    adv_setting.search_adv_id = "test_search_adv_id"
    
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
    
    # Патчим все необходимые функции
    with patch('app.modules.wb_adv_updater.data_manager.get_min_ctr', mock_get_min_ctr), \
         patch('app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.get_keywords_spend', mock_get_keywords_spend), \
         patch('app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.get_stats_by_last_days', mock_get_stats_by_last_days), \
         patch('app.modules.shop_runner.wb_statistic_manager.backend.common_stat_manager.get_stats_for_last_period', mock_get_stats_for_last_period), \
         patch('app.modules.common_advs_stat.data_manager._sm', return_value=mock_async_session_cm):
        
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
        assert result.auction_cpm == 300.0
        assert result.total_spend == 200.0  # 100.0 (auto) + 100.0 (auction)
        assert result.addition_spend_in_adv == 0.0  # 100.0 - 100.0
        assert result.all_orders_for_last_3_days == 20
        assert result.mean_orders_for_3_days is not None
        assert result.mean_price_for_order is not None
        assert result.spend_for_inner_adv_for_3_days == 200.0
        assert isinstance(result.full_adv_stat_for_last_3_days_for_auto_adv, SmallFullAdvStat)
        assert isinstance(result.full_adv_stat_for_last_3_days_for_auction, SmallFullAdvStat)
        assert isinstance(result.common_stat, CommonCardStat)

@pytest.mark.asyncio
async def test_get_campaign_efficiency_score():
    """Тест для расчета показателя эффективности кампании"""
    
    # Создаем моки объектов
    # ... existing code ... 