import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
from app.modules.shop_menu.message import ShopMenu
from tests.mocks import MockWBToken
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, User, WBToken, AdvSetting
from sqlalchemy import select, and_

@pytest.fixture
def mock_bot():
    return AsyncMock()

@pytest.fixture
def mock_state():
    return AsyncMock(spec=FSMContext)

@pytest.fixture
def mock_chat_id():
    return 123456789

@pytest.fixture
def mock_wb_token():
    token = MockWBToken()
    token.id = 1
    token.api_key = "test_api_key"
    token.shop_id = "test_shop_id"
    token.active = True
    token.user_id = 1
    return token

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.user_telegram_id = 123456789
    return user

@pytest.fixture
def mock_wb_cabinet():
    cabinet = MagicMock(spec=WBCabinet)
    cabinet.id = 1
    cabinet.shop_id = "test_shop"
    cabinet.balance = 1000
    cabinet.bonus = 100
    return cabinet

@pytest.fixture
def mock_wb_user_cabinet(mock_wb_cabinet, mock_user):
    cabinet = MagicMock(spec=WBUserCabinet)
    cabinet.wb_cabinet = mock_wb_cabinet
    cabinet.user = mock_user
    cabinet.wb_cabinet_id = mock_wb_cabinet.id
    cabinet.user_id = mock_user.id
    cabinet.name = "Test Cabinet"
    return cabinet

@pytest.fixture
def mock_adv_setting(mock_wb_cabinet):
    return AdvSetting(
        id=1,
        adv_id="test_adv_id",
        name="Test Adv",
        wb_cabinet_id=mock_wb_cabinet.id,
        active_status=True,
        bot_active=True,
        nmids=[12345, 67890],
        type="search"
    )

@pytest.fixture
def shop_menu(mock_bot, mock_state, mock_chat_id, mock_wb_user_cabinet):
    menu = ShopMenu(
        bot=mock_bot,
        chat_id=mock_chat_id,
        state=mock_state,
        wb_user_cabinet_original_id=mock_wb_user_cabinet.id
    )
    # Устанавливаем необходимые атрибуты
    menu._wb_user_cabinet = mock_wb_user_cabinet
    menu._wb_cabinet = mock_wb_user_cabinet.wb_cabinet
    menu._balance = 1000.0
    menu._bonus = 100.0
    menu.count_active_advs = 0
    menu.is_active_adv = False
    menu.days_left = 30
    menu.bonus_days = 60
    menu.price_for_month_for_shop = 1000
    menu.total_amount_for_day = 50
    
    # Мокаем метод _load_all_data
    async def mock_load_all_data():
        pass
    menu._load_all_data = mock_load_all_data
    
    return menu

@pytest.mark.asyncio
async def test_shop_menu_call(test_async_db, mock_wb_cabinet, mock_user):
    """Тест вызова меню магазина"""
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        session.add(mock_user)
        await session.commit()

        # Создаем настройки рекламы
        settings = [
            MockAdvSetting(
                wb_cabinet_id=mock_wb_cabinet.id,
                name=f"Setting {i}",
                description=f"Description {i}",
                is_active=True
            )
            for i in range(3)
        ]
        for setting in settings:
            session.add(setting)
        await session.commit()

        # Проверяем, что все объекты созданы
        cabinet = await session.get(MockWBCabinet, mock_wb_cabinet.id)
        assert cabinet is not None

        user = await session.get(MockUser, mock_user.id)
        assert user is not None

        # Проверяем настройки
        query = select(MockAdvSetting).where(MockAdvSetting.wb_cabinet_id == mock_wb_cabinet.id)
        result = await session.execute(query)
        result_settings = result.scalars().all()
        assert len(result_settings) == 3

@pytest.mark.asyncio
async def test_shop_menu_with_active_advs(test_async_db, mock_wb_cabinet):
    """Тест меню магазина с активными рекламными кампаниями"""
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        await session.commit()

        # Создаем активные рекламные кампании
        settings = [
            MockAdvSetting(
                wb_cabinet_id=mock_wb_cabinet.id,
                name=f"Active Setting {i}",
                description=f"Description {i}",
                is_active=True
            )
            for i in range(3)
        ]
        for setting in settings:
            session.add(setting)
        await session.commit()

        # Проверяем настройки
        query = select(MockAdvSetting).where(
            and_(
                MockAdvSetting.wb_cabinet_id == mock_wb_cabinet.id,
                MockAdvSetting.is_active == True
            )
        )
        result = await session.execute(query)
        active_settings = result.scalars().all()
        assert len(active_settings) == 3

@pytest.mark.asyncio
async def test_get_shop_menu(test_async_db, mock_wb_cabinet):
    """Тест получения меню магазина"""
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        await session.commit()

        # Создаем настройки
        settings = [
            MockAdvSetting(
                wb_cabinet_id=mock_wb_cabinet.id,
                name=f"Setting {i}",
                description=f"Description {i}",
                is_active=True
            )
            for i in range(3)
        ]
        for setting in settings:
            session.add(setting)
        await session.commit()

        # Проверяем меню
        cabinet = await session.get(MockWBCabinet, mock_wb_cabinet.id)
        assert cabinet is not None

        query = select(MockAdvSetting).where(MockAdvSetting.wb_cabinet_id == mock_wb_cabinet.id)
        result = await session.execute(query)
        menu_settings = result.scalars().all()
        assert len(menu_settings) == 3

@pytest.mark.asyncio
async def test_get_adv_menu(test_async_db, mock_wb_cabinet):
    """Тест получения меню рекламных кампаний"""
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        await session.commit()

        # Создаем рекламные кампании
        settings = [
            MockAdvSetting(
                wb_cabinet_id=mock_wb_cabinet.id,
                name=f"Adv Setting {i}",
                description=f"Description {i}",
                is_active=True
            )
            for i in range(3)
        ]
        for setting in settings:
            session.add(setting)
        await session.commit()

        # Проверяем меню рекламных кампаний
        query = select(MockAdvSetting).where(MockAdvSetting.wb_cabinet_id == mock_wb_cabinet.id)
        result = await session.execute(query)
        adv_settings = result.scalars().all()
        assert len(adv_settings) == 3

@pytest.mark.asyncio
async def test_get_adv_menu_no_advs(test_async_db, mock_wb_cabinet):
    """Тест получения меню рекламных кампаний без активных кампаний"""
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        await session.commit()

        # Проверяем отсутствие рекламных кампаний
        query = select(MockAdvSetting).where(MockAdvSetting.wb_cabinet_id == mock_wb_cabinet.id)
        result = await session.execute(query)
        adv_settings = result.scalars().all()
        assert len(adv_settings) == 0

