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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._avg_position = 2.5

    @property
    def spend(self):
        return self.sum

    @property
    def avg_position(self):
        return self._avg_position
        
    @avg_position.setter
    def avg_position(self, value):
        self._avg_position = value

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
        
        # Проверяем заполнение план-вектора и факт-вектора
        assert "orders" in result.plan_vector
        assert "cpo" in result.plan_vector
        assert "orders" in result.fact_vector
        assert "cpo" in result.fact_vector
        
        # Проверяем значения в план-векторе
        assert result.plan_vector["orders"] == getattr(adv_setting, 'target_orders_per_day', 10)
        assert result.plan_vector["cpo"] == getattr(adv_setting, 'target_cpo', 100)
        
        # Проверяем значения в факт-векторе
        assert result.fact_vector["orders"] == result.mean_orders_for_3_days
        assert result.fact_vector["cpo"] == result.mean_price_for_order

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
    
    # Вычисляем расстояние между векторами
    distance = data.calculate_vector_distance()
    
    # Проверяем, что расстояние положительное и не слишком большое
    assert distance > 0
    assert distance < 100  # Максимальное ожидаемое значение

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

@pytest.mark.asyncio
async def test_calculate_diff_to_plan_for_adv_settings():
    """Тест для проверки расчета отклонения от плана для списка настроек рекламы"""
    
    # Создаем тестовые AdvSetting
    adv_settings = [
        AdvSetting(id=1, adv_id=1, nmids=[123]),  # Будет с идеальными показателями
        AdvSetting(id=2, adv_id=2, nmids=[123]),  # Будет с заказами ниже плана (небольшое отклонение)
        AdvSetting(id=3, adv_id=3, nmids=[123]),  # Будет с заказами сильно ниже плана
        AdvSetting(id=4, adv_id=4, nmids=[123]),  # Будет с высокой себестоимостью
        AdvSetting(id=5, adv_id=5, nmids=[123])   # Будет с отсутствующими данными
    ]
    
    # Создаем общую статистику с векторами плана и факта
    common_stat = MagicMock(spec=CommonAdvsStatData)
    common_stat.plan_vector = {"orders": 10, "cpo": 50}
    common_stat.fact_vector = {"orders": 10, "cpo": 30}
    
    # Для каждого случая устанавливаем разные значения mean_orders_for_3_days и mean_price_for_order
    # Значения будут меняться в зависимости от текущего adv_setting в цикле
    common_stat.mean_orders_for_3_days = 10  # Начальное значение
    common_stat.mean_price_for_order = 30    # Начальное значение
    
    # Фиктивный объект статистики
    full_adv_stat = MagicMock()
    
    # Создаем экземпляр менеджера
    manager = CommonAdvsStatDataManager()
    
    # Проверка для id=1: Идеальные показатели (заказы = план, себестоимость < план)
    common_stat.mean_orders_for_3_days = 10  # Равно плану
    common_stat.mean_price_for_order = 30    # Ниже плана
    result = await manager.calculate_diff_to_plan_for_adv_settings([adv_settings[0]], common_stat, full_adv_stat)
    assert result[0].diff_to_plan == 0.0  # Идеальный случай - 0
    
    # Проверка для id=2: Заказы немного ниже плана (отклонение < 50%)
    common_stat.mean_orders_for_3_days = 7   # Ниже плана на 30%
    common_stat.mean_price_for_order = 40    # Ниже плана
    result = await manager.calculate_diff_to_plan_for_adv_settings([adv_settings[1]], common_stat, full_adv_stat)
    assert result[0].diff_to_plan == 0.3  # Отклонение 30%
    
    # Проверка для id=3: Заказы сильно ниже плана (отклонение > 50%)
    common_stat.mean_orders_for_3_days = 4   # Ниже плана на 60%
    common_stat.mean_price_for_order = 40    # Не важно, т.к. заказы сильно ниже плана
    result = await manager.calculate_diff_to_plan_for_adv_settings([adv_settings[2]], common_stat, full_adv_stat)
    assert result[0].diff_to_plan == 1.5  # Высокий приоритет из-за низких заказов
    
    # Проверка для id=4: Высокая себестоимость
    common_stat.mean_orders_for_3_days = 12  # Выше плана
    common_stat.mean_price_for_order = 75    # Выше плана на 50%
    result = await manager.calculate_diff_to_plan_for_adv_settings([adv_settings[3]], common_stat, full_adv_stat)
    assert result[0].diff_to_plan == 0.5  # Отклонение по себестоимости
    
    # Проверка для id=5: Отсутствующие данные (mean_orders_for_3_days = None)
    common_stat.mean_orders_for_3_days = None
    common_stat.mean_price_for_order = 50
    result = await manager.calculate_diff_to_plan_for_adv_settings([adv_settings[4]], common_stat, full_adv_stat)
    assert result[0].diff_to_plan == 1.0  # Стандартное отклонение при отсутствии данных

@pytest.mark.asyncio
async def test_calculate_diff_to_plan_for_adv_settings_no_data():
    """Тест для проверки расчета отклонения от плана при отсутствии данных"""
    
    # Создаем тестовые AdvSetting
    adv_settings = [
        AdvSetting(id=1, adv_id=1, nmids=[123]),
        AdvSetting(id=2, adv_id=2, nmids=[123])
    ]
    
    # Создаем экземпляр менеджера
    manager = CommonAdvsStatDataManager()
    
    # Вызываем метод без данных
    result = await manager.calculate_diff_to_plan_for_adv_settings(adv_settings, None, None)
    
    # Проверяем результаты
    assert len(result) == 2
    assert result[0].diff_to_plan == 2.0  # Максимальное отклонение при полном отсутствии данных
    assert result[1].diff_to_plan == 2.0  # Максимальное отклонение при полном отсутствии данных

@pytest.mark.asyncio
async def test_get_data_with_small_full_adv_stat():
    # Создаем моки для всех необходимых функций
    mock_get_min_ctr = AsyncMock()
    mock_get_min_ctr.return_value = 0.5

    mock_get_keywords_spend = AsyncMock()
    mock_get_keywords_spend.return_value = 100.0

    mock_get_stats_by_last_days = AsyncMock()
    mock_get_stats_for_last_period = AsyncMock()

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

    # Создаем тестовые данные
    adv_setting = MagicMock()
    adv_setting.adv_id = "test_adv_id"
    adv_setting.search_adv_id = "test_search_adv_id"
    adv_setting.nmids = [12345]

    keywords = [
        CalculatedKeyword(
            text="test1",
            views=100,
            clicks=10,
            spend=50.0,
            status=0
        )
    ]

    # Патчим все необходимые функции
    with patch('app.modules.wb_adv_updater.data_manager.get_min_ctr', mock_get_min_ctr), \
         patch('app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.get_keywords_spend', mock_get_keywords_spend), \
         patch('app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.get_stats_by_last_days', mock_get_stats_by_last_days), \
         patch('app.modules.shop_runner.wb_statistic_manager.backend.common_stat_manager.get_stats_for_last_period', mock_get_stats_for_last_period), \
         patch('app.modules.common_advs_stat.data_manager._sm', return_value=mock_async_session_cm):

        # Проверяем, что при использовании SmallFullAdvStat без avg_position возникает ошибка
        with pytest.raises(AttributeError, match="'SmallFullAdvStat' object has no attribute 'avg_position'"):
            await CommonAdvsStatDataManager.get_data(adv_setting, keywords) 