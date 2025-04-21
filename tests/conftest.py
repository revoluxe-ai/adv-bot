import dotenv
dotenv.load_dotenv()
import os
import sys
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Устанавливаем версию pandas чтобы избежать AttributeError: __version__
import pandas as pd
if not hasattr(pd, '__version__'):
    pd.__version__ = '1.5.3'

# Мокируем SQLAlchemy для решения проблемы метаклассов
class MockJSONMixin:
    def __init__(self, *args, **kwargs):
        pass

class MockJSON:
    JSONIndexType = MockJSONMixin
    JSONPathType = MockJSONMixin

# Патчим модули SQLAlchemy, которые вызывают конфликт метаклассов
sys.modules['sqlalchemy.dialects.sqlite.json'] = MagicMock(
    JSON=MockJSON,
    JSONIndexType=MockJSONMixin,
    JSONPathType=MockJSONMixin,
    _FormatTypeMixin=MockJSONMixin
)

# Создадим мок для sklearn и зависимых модулей
class MockModules:
    pass

class MockXGBModel:
    def predict(self, X):
        return [0.1] * len(X)

# Мокирование модулей, которые вызывают проблемы
sys.modules['sklearn'] = MockModules()
sys.modules['sklearn.model_selection'] = MockModules()
sys.modules['sklearn.preprocessing'] = MockModules()
sys.modules['sklearn.pipeline'] = MockModules()
sys.modules['xgboost'] = type('MockXGBoost', (), {
    'XGBModel': MockXGBModel, 
    'XGBRegressor': MockXGBModel
})

# Создаем мок для функции load_model
def mock_load_model():
    return MockXGBModel()

# Мок для функции save_model
def mock_save_model(model, time_stamp=None):
    pass

# Патчим импорт ml_common_funcs.load_model
sys.modules['app.modules.wb_adv_updater.ml_common_funcs'] = type('MockMLCommonFuncs', (), {
    'load_model': mock_load_model,
    'save_model': mock_save_model,
    'get_keyword_features': AsyncMock(return_value={})
})

# Мок для fitter модуля
class MockFitter:
    def __init__(self, *args, **kwargs):
        pass
    
    def fill_average_vector(self, *args, **kwargs):
        return pd.DataFrame()

sys.modules['app.modules.wb_adv_updater.fitter'] = type('MockFitter', (), {
    'Fitter': MockFitter
})

# Мок для data_manager модуля
class MockDataGetter:
    async def get_keyword_features_from_redis(self, *args, **kwargs):
        return []
    
    async def get_nmid_to_item_features(self, *args, **kwargs):
        return {}

class MockDataManager:
    async def get_min_ctr(self, *args, **kwargs):
        return 0.01
    
    async def get_keyword_statistic(self, *args, **kwargs):
        return 1, 100, {}

sys.modules['app.modules.wb_adv_updater.data_manager'] = type('MockDataManager', (), {
    'DataGetter': MockDataGetter,
    'get_min_ctr': AsyncMock(return_value=0.01),
    'get_keyword_statistic': AsyncMock(return_value=(1, 100, {}))
})

# Мок для ML модуля
class MockPredictor:
    async def predict_ctr_for_keywords(self):
        pass

    async def _get_df_for_predict(self, *args, **kwargs):
        return pd.DataFrame()

sys.modules['app.modules.wb_adv_updater.ML'] = type('MockML', (), {
    'Predictor': MockPredictor
})

from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from tests.mocks import MockBase, MockItemFeature, MockKeywordFeature, MockWBCabinet, MockUser, MockWBUserCabinet, MockWBToken, MockAdvSetting, MockAdvPayment
import app.modules.wb_adv_updater.models as models
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Add the project root directory to PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Моксируем модуль keywords_query, который пытается загрузить CSV-файл
sys.modules['app.modules.keywords_query.keywords_query'] = MagicMock(
    queries_dict={
        'test_keyword': 100,
        'another_keyword': 200,
        'last_keyword': 50
    },
    min_query=50,
    get_query_freq=MagicMock(return_value=100)
)
sys.modules['app.modules.keywords_query'] = MagicMock(
    keywords_query=sys.modules['app.modules.keywords_query.keywords_query']
)

# Заменяем оригинальные модели на моки для тестов
models.ItemFeature = MockItemFeature
models.KeywordFeature = MockKeywordFeature
models.WBCabinet = MockWBCabinet
models.WBUserCabinet = MockWBUserCabinet
models.User = MockUser
models.WBToken = MockWBToken
models.AdvSetting = MockAdvSetting

# Заменяем модели в модуле wildberries
from app.modules.common_slaves.wildberries import models as wb_models
wb_models.WBCabinet = MockWBCabinet
wb_models.WBUserCabinet = MockWBUserCabinet
wb_models.User = MockUser
wb_models.WBToken = MockWBToken
wb_models.AdvSetting = MockAdvSetting
wb_models.AdvPayment = MockAdvPayment

# Заменяем модели в модуле messages
from app.client_bot.user_interface.views import messages
messages.User = MockUser
messages.WBUserCabinet = MockWBUserCabinet
messages.WBCabinet = MockWBCabinet
messages.WBToken = MockWBToken
messages.AdvSetting = MockAdvSetting

# Заменяем модели в модуле wb_adv_updater
from app.modules.wb_adv_updater import models as adv_models
adv_models.AdvPayment = MockAdvPayment

# Мокируем зависимости для SQLite
sys.modules['sqlalchemy.dialects.sqlite'] = MagicMock()
sys.modules['sqlalchemy.dialects.sqlite.base'] = MagicMock()
sys.modules['sqlalchemy.dialects.sqlite.aiosqlite'] = MagicMock()

@pytest.fixture
def mock_wb_cabinet():
    return MockWBCabinet(
        id=1,
        shop_id="test_shop",
        active=True,
        expiration_time=datetime.now() + timedelta(days=30),
        demo=True,
        balance=1000.0,
        bonus=100.0,
        white_list_update_active=True
    )

@pytest.fixture
def mock_user():
    return MockUser(
        id=1,
        user_telegram_id=123456789,
        username="test_user"
    )

@pytest.fixture
def mock_wb_user_cabinet(mock_user, mock_wb_cabinet):
    return MockWBUserCabinet(
        id=1,
        user=mock_user,
        wb_cabinet=mock_wb_cabinet,
        active=True
    )

@pytest.fixture
def mock_adv_setting(mock_wb_cabinet):
    return MockAdvSetting(
        id=1,
        adv_id="test_adv_id",
        name="Test Adv",
        wb_cabinet_id=mock_wb_cabinet.id,
        active_status=True,
        bot_active=True,
        nmids=[12345, 67890],
        type="search"
    )

# Изменяем создание тестовой базы данных
class MockAsyncEngine:
    async def begin(self):
        class MockContext:
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
            async def run_sync(self, func):
                pass
        return MockContext()
        
    def dispose(self):
        pass

class MockAsyncSession:
    def __init__(self):
        self.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(
                all=MagicMock(return_value=[])
            )),
            unique=MagicMock(return_value=MagicMock())
        ))
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.close = AsyncMock()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def add(self, obj):
        pass
        
    async def get(self, model, id):
        return None

@pytest_asyncio.fixture
async def test_async_db():
    """Фикстура для создания тестовой базы данных"""
    # Создаем мок для базы данных вместо реальной
    session = MockAsyncSession()
    yield session

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield loop
    if not loop.is_closed():
        loop.close()

@pytest.fixture(autouse=True)
def patch_get_async_session_maker(monkeypatch, test_async_db):
    """Патчим get_async_session_maker, чтобы он использовал тестовую БД"""
    async def mock_get_async_session_maker(*args, **kwargs):
        return test_async_db
    
    monkeypatch.setattr("app.utils.db.session_maker.get_async_session_maker", mock_get_async_session_maker)
    monkeypatch.setattr("app.client_bot.user_interface.views.messages._sm", mock_get_async_session_maker)

@pytest.fixture
def mock_session():
    """Создает мок для сессии SQLAlchemy"""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.get = AsyncMock()
    session.add = MagicMock()
    return session 

@pytest.fixture(autouse=True)
def mock_wb_parser():
    """Мок для парсера WB API"""
    mock_response = {
        'data': {
            'products': [
                {
                    'id': 12345,
                    'log': {
                        'advertId': 'test_adv_id',
                        'cpm': 100,
                        'position': 1,
                        'promoPosition': 1,
                        'tp': 'c'
                    }
                }
            ],
            'total': 100
        }
    }
    
    with patch('app.modules.wb_keywords_parser.parser.ParserService._ParserService__parse_keywords_from_wb', 
              new_callable=AsyncMock, 
              return_value=(mock_response['data']['products'], 'test_cluster', 'test_preset', mock_response['data']['total'])):
        yield
