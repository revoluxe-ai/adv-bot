import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from app.modules.common_advs_stat.data_manager import CommonAdvsStatDataManager
# from app.modules.common_advs_stat.data_classes import CommonAdvsStatData
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat

# Создаем имитацию класса CommonAdvsStatData
class CommonAdvsStatData:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# Создаем фикстуру для создания модифицированного FullAdvStat
@pytest.fixture
def create_test_full_adv_stat():
    def _create_test_full_adv_stat(**kwargs):
        full_adv_stat = FullAdvStat(**kwargs)
        # Добавляем дополнительные свойства через monkey patching
        full_adv_stat._spend = full_adv_stat.sum
        full_adv_stat._avg_position = 2.5
        
        # Добавляем свойство spend
        def get_spend(self):
            return self._spend
            
        def set_spend(self, value):
            self._spend = value
        
        # Добавляем свойство avg_position
        def get_avg_position(self):
            return self._avg_position
            
        def set_avg_position(self, value):
            self._avg_position = value
            
        # Присоединяем свойства
        FullAdvStat.spend = property(get_spend, set_spend)
        FullAdvStat.avg_position = property(get_avg_position, set_avg_position)
        
        return full_adv_stat
    return _create_test_full_adv_stat


# Создаем фикстуру для создания модифицированного AdvSetting
@pytest.fixture
def create_test_adv_setting():
    def _create_test_adv_setting(**kwargs):
        # Вместо создания экземпляра AdvSetting, создаем MagicMock
        mock_adv_setting = MagicMock()
        
        # Задаем все атрибуты из kwargs
        for key, value in kwargs.items():
            if key == '_search_adv_id':
                # Для search_adv_id используем PropertyMock
                type(mock_adv_setting).search_adv_id = PropertyMock(return_value=value)
            else:
                setattr(mock_adv_setting, key, value)
                
        # Явно добавляем свойство cpm
        if 'cpm' not in kwargs:
            mock_adv_setting.cpm = 200
            
        return mock_adv_setting
    return _create_test_adv_setting


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
async def test_get_data(create_test_full_adv_stat, create_test_adv_setting):
    # Создаем моки для всех необходимых функций
    mock_get_min_ctr = AsyncMock()
    mock_get_min_ctr.return_value = 0.5
    
    mock_get_keywords_spend = AsyncMock()
    # Определяем разные возвращаемые значения в зависимости от аргументов
    async def side_effect_get_keywords_spend(adv_ids, days=None, date_from=None, date_to=None):
        if adv_ids == ["test_adv_id"]:  # Для auto рекламы
            return 100.0
        elif adv_ids == ["test_search_adv_id"]:  # Для search рекламы (аукцион)
            return 100.0
        return 0.0
    
    mock_get_keywords_spend.side_effect = side_effect_get_keywords_spend
    
    mock_get_stats_by_last_days = AsyncMock()
    # Определяем разные возвращаемые значения в зависимости от аргументов
    async def side_effect_get_stats(adv_ids, days=None, date_from=None):
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
    mock_get_stats_for_last_period.return_value = create_test_full_adv_stat(
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
    mock_result.scalar_one_or_none = MagicMock(return_value=200.0)
    mock_session.execute = AsyncMock(return_value=mock_result)
    
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
         patch('app.modules.common_advs_stat.data_manager._sm', return_value=mock_async_session_cm), \
         patch('app.modules.common_advs_stat.data_manager.select', MagicMock(return_value=MagicMock())), \
         patch('app.modules.common_advs_stat.data_manager.AdvSetting', MagicMock(cpm=MagicMock())), \
         patch('app.modules.common_advs_stat.data_manager.CommonAdvsStatData', CommonAdvsStatData):
        
        # Создаем тестовые данные
        adv_setting = create_test_adv_setting(
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
                spend=50.0
            ),
            CalculatedKeyword(
                text="test2",
                views=200,
                clicks=20,
                spend=100.0,
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
        assert result.all_orders == 20
        assert result.mean_orders_for_3_days is not None
        assert result.mean_price_for_order is not None
        assert result.spend_for_inner_adv_for_3_days == 200.0
        assert isinstance(result.full_adv_stat_for_auto_adv, FullAdvStat)
        assert isinstance(result.full_adv_stat_for_auction, FullAdvStat)
        assert isinstance(result.common_stat, FullAdvStat)

