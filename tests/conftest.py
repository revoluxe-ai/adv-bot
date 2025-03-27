import os
import sys
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base
from app.utils.db.base import Base
from app.utils.db.session_maker import get_async_session_maker
from tests.mocks import MockBase, MockItemFeature, MockKeywordFeature, MockWBCabinet, MockUser, MockWBUserCabinet, MockWBToken, MockAdvSetting, MockAdvPayment
import app.modules.wb_adv_updater.models as models
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, User, WBToken, AdvSetting
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Add the project root directory to PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

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

@pytest.fixture(scope="session")
async def test_db():
    """Create a test database and tables."""
    # Создаем движок SQLite в памяти
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(MockBase.metadata.drop_all)
        await conn.run_sync(MockBase.metadata.create_all)

    # Создаем сессию
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

@pytest.fixture(scope="function")
async def test_async_db():
    """Create a test database and tables."""
    # Создаем движок SQLite в памяти
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(MockBase.metadata.drop_all)
        await conn.run_sync(MockBase.metadata.create_all)

    # Создаем сессию
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session 

@pytest.fixture(autouse=True)
def patch_get_async_session_maker(monkeypatch, test_async_db):
    """Патчим get_async_session_maker, чтобы он использовал тестовую БД"""
    @asynccontextmanager
    async def mock_get_async_session_maker(*args, **kwargs):
        yield test_async_db
    
    monkeypatch.setattr("app.utils.db.session_maker.get_async_session_maker", mock_get_async_session_maker)
    monkeypatch.setattr("app.client_bot.user_interface.views.messages._sm", mock_get_async_session_maker) 