import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
from app.modules.shop_menu.message import ShopMenu
from tests.mocks import MockUser, MockWBCabinet, MockWBUserCabinet, MockWBToken, MockAdvSetting
import json
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, User, WBToken, AdvSetting
from sqlalchemy.ext.asyncio import AsyncSession

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
async def test_shop_menu_call(test_async_db):
    async with test_async_db as session:
        current_time = datetime.now().replace(microsecond=0)
        wb_cabinet = WBCabinet(
            id=1,
            balance=1000.0,
            bonus=100.0,
            expiration_time=current_time + timedelta(days=30),
            active=True,
            shop_id="test_shop",
            demo=True,
            white_list_update_active=False
        )
        user = User(id=1, user_telegram_id=123456789, username="test_user")
        wb_user_cabinet = WBUserCabinet(id=1, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
        wb_token = WBToken(id=1, api_key="test_key", user_id=1, active=True, shop_id="test_shop")
        
        session.add(wb_cabinet)
        session.add(user)
        session.add(wb_user_cabinet)
        session.add(wb_token)
        await session.commit()
        
        # Обновляем объекты и их связи
        await session.refresh(wb_cabinet)
        await session.refresh(user)
        await session.refresh(wb_user_cabinet)
        await session.refresh(wb_token)
        
        # Устанавливаем связи
        wb_user_cabinet.wb_cabinet = wb_cabinet
        wb_user_cabinet.user = user
        wb_token.user = user
        await session.commit()

        mock_bot = AsyncMock()
        mock_state = AsyncMock()
        mock_chat_id = 123456789

        shop_menu = ShopMenu(
            bot=mock_bot,
            chat_id=mock_chat_id,
            state=mock_state,
            wb_user_cabinet_original_id=1
        )

        # Мокаем метод _load_all_data
        async def mock_load_all_data():
            shop_menu._wb_user_cabinet = wb_user_cabinet
            shop_menu._wb_cabinet = wb_cabinet
            shop_menu._balance = 1000.0
            shop_menu._bonus = 100.0
            shop_menu.count_active_advs = 0
            shop_menu.is_active_adv = False
            shop_menu.days_left = 30
            shop_menu.bonus_days = 60
            shop_menu.price_for_month_for_shop = 1000
            shop_menu.total_amount_for_day = 50
            return True

        shop_menu._load_all_data = mock_load_all_data

        result = await shop_menu()
        assert "Магазин" in shop_menu.text
        assert "Test Cabinet" in shop_menu.text
        assert "1000 рублей" in shop_menu.text

@pytest.mark.asyncio
async def test_shop_menu_with_active_advs(test_async_db):
    async with test_async_db as session:
        current_time = datetime.now().replace(microsecond=0)
        wb_cabinet = WBCabinet(
            id=1,
            balance=1000.0,
            bonus=100.0,
            expiration_time=current_time + timedelta(days=30),
            active=True,
            shop_id="test_shop",
            demo=True,
            white_list_update_active=False
        )
        user = User(id=1, user_telegram_id=123456789, username="test_user")
        wb_user_cabinet = WBUserCabinet(id=1, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
        wb_token = WBToken(id=1, api_key="test_key", user_id=1, active=True, shop_id="test_shop")
        adv_setting = AdvSetting(
            id=1,
            name="Test Adv",
            wb_cabinet_id=1,
            last_update=current_time,
            bot_active=True,
            active_status="active",
            new_auto_min_ctr_mode=True,
            exponent_predict_ctr=3.0,
            auction_boost_all_phrase_mode=False
        )
        
        session.add(wb_cabinet)
        session.add(user)
        session.add(wb_user_cabinet)
        session.add(wb_token)
        session.add(adv_setting)
        await session.commit()
        
        # Обновляем объекты и их связи
        await session.refresh(wb_cabinet)
        await session.refresh(user)
        await session.refresh(wb_user_cabinet)
        await session.refresh(wb_token)
        await session.refresh(adv_setting)
        
        # Устанавливаем связи
        wb_user_cabinet.wb_cabinet = wb_cabinet
        wb_user_cabinet.user = user
        wb_token.user = user
        adv_setting.wb_cabinet = wb_cabinet
        await session.commit()

        mock_bot = AsyncMock()
        mock_state = AsyncMock()
        mock_chat_id = 123456789

        shop_menu = ShopMenu(
            bot=mock_bot,
            chat_id=mock_chat_id,
            state=mock_state,
            wb_user_cabinet_original_id=1
        )

        # Мокаем метод _load_all_data
        async def mock_load_all_data():
            shop_menu._wb_user_cabinet = wb_user_cabinet
            shop_menu._wb_cabinet = wb_cabinet
            shop_menu._balance = 1000.0
            shop_menu._bonus = 100.0
            shop_menu.count_active_advs = 1
            shop_menu.is_active_adv = True
            shop_menu.days_left = 30
            shop_menu.bonus_days = 60
            shop_menu.price_for_month_for_shop = 1000
            shop_menu.total_amount_for_day = 50
            return True

        shop_menu._load_all_data = mock_load_all_data

        result = await shop_menu()
        assert "Test Cabinet" in shop_menu.text
        assert "1000 рублей" in shop_menu.text
        assert "1" in shop_menu.text  # Проверяем количество активных кампаний

@pytest.mark.asyncio
async def test_get_shop_menu(mock_bot, mock_state, mock_chat_id, test_async_db):
    async with test_async_db as session:
        current_time = datetime.now().replace(microsecond=0)
        wb_cabinet = WBCabinet(
            id=1,
            balance=1000.0,
            bonus=100.0,
            expiration_time=current_time + timedelta(days=30),
            active=True,
            shop_id="test_shop",
            demo=True,
            white_list_update_active=False
        )
        user = User(id=1, user_telegram_id=123456789, username="test_user")
        wb_user_cabinet = WBUserCabinet(id=1, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
        wb_token = WBToken(id=1, api_key="test_key", user_id=1, active=True, shop_id="test_shop")
        
        session.add(wb_cabinet)
        session.add(user)
        session.add(wb_user_cabinet)
        session.add(wb_token)
        await session.commit()
        
        # Обновляем объекты и их связи
        await session.refresh(wb_cabinet)
        await session.refresh(user)
        await session.refresh(wb_user_cabinet)
        await session.refresh(wb_token)
        
        # Устанавливаем связи
        wb_user_cabinet.wb_cabinet = wb_cabinet
        wb_user_cabinet.user = user
        wb_token.user = user
        await session.commit()

        mock_bot = AsyncMock()
        mock_state = AsyncMock()
        mock_chat_id = 123456789

        shop_menu = ShopMenu(
            bot=mock_bot,
            chat_id=mock_chat_id,
            state=mock_state,
            wb_user_cabinet_original_id=1
        )

        # Мокаем метод _load_all_data
        async def mock_load_all_data():
            shop_menu._wb_user_cabinet = wb_user_cabinet
            shop_menu._wb_cabinet = wb_cabinet
            shop_menu._balance = 1000.0
            shop_menu._bonus = 100.0
            shop_menu.count_active_advs = 0
            shop_menu.is_active_adv = False
            shop_menu.days_left = 30
            shop_menu.bonus_days = 60
            shop_menu.price_for_month_for_shop = 1000
            shop_menu.total_amount_for_day = 50
            return True

        shop_menu._load_all_data = mock_load_all_data

        result = await shop_menu()
        assert "Test Cabinet" in shop_menu.text
        assert "1000 рублей" in shop_menu.text

@pytest.mark.asyncio
async def test_get_adv_menu(mock_bot, mock_state, mock_chat_id, test_async_db):
    async with test_async_db as session:
        current_time = datetime.now().replace(microsecond=0)
        wb_cabinet = WBCabinet(
            id=1,
            balance=1000.0,
            bonus=100.0,
            expiration_time=current_time + timedelta(days=30),
            active=True,
            shop_id="test_shop",
            demo=True,
            white_list_update_active=False
        )
        user = User(id=1, user_telegram_id=123456789, username="test_user")
        wb_user_cabinet = WBUserCabinet(id=1, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
        wb_token = WBToken(id=1, api_key="test_key", user_id=1, active=True, shop_id="test_shop")
        adv_setting = AdvSetting(
            id=1,
            name="Test Adv",
            wb_cabinet_id=1,
            last_update=current_time,
            bot_active=True,
            active_status="active",
            new_auto_min_ctr_mode=True,
            exponent_predict_ctr=3.0,
            auction_boost_all_phrase_mode=False
        )
        
        session.add(wb_cabinet)
        session.add(user)
        session.add(wb_user_cabinet)
        session.add(wb_token)
        session.add(adv_setting)
        await session.commit()
        
        # Обновляем объекты и их связи
        await session.refresh(wb_cabinet)
        await session.refresh(user)
        await session.refresh(wb_user_cabinet)
        await session.refresh(wb_token)
        await session.refresh(adv_setting)
        
        # Устанавливаем связи
        wb_user_cabinet.wb_cabinet = wb_cabinet
        wb_user_cabinet.user = user
        wb_token.user = user
        adv_setting.wb_cabinet = wb_cabinet
        await session.commit()

        mock_bot = AsyncMock()
        mock_state = AsyncMock()
        mock_chat_id = 123456789

        shop_menu = ShopMenu(
            bot=mock_bot,
            chat_id=mock_chat_id,
            state=mock_state,
            wb_user_cabinet_original_id=1
        )

        # Мокаем метод _load_all_data
        async def mock_load_all_data():
            shop_menu._wb_user_cabinet = wb_user_cabinet
            shop_menu._wb_cabinet = wb_cabinet
            shop_menu._balance = 1000.0
            shop_menu._bonus = 100.0
            shop_menu.count_active_advs = 1
            shop_menu.is_active_adv = True
            shop_menu.days_left = 30
            shop_menu.bonus_days = 60
            shop_menu.price_for_month_for_shop = 1000
            shop_menu.total_amount_for_day = 50
            return True

        shop_menu._load_all_data = mock_load_all_data

        result = await shop_menu()
        assert "Test Cabinet" in shop_menu.text
        assert "1000 рублей" in shop_menu.text
        assert "1" in shop_menu.text  # Проверяем количество активных кампаний

@pytest.mark.asyncio
async def test_get_adv_menu_no_advs(mock_bot, mock_state, mock_chat_id, test_async_db):
    async with test_async_db as session:
        current_time = datetime.now().replace(microsecond=0)
        wb_cabinet = WBCabinet(
            id=1,
            balance=1000.0,
            bonus=100.0,
            expiration_time=current_time + timedelta(days=30),
            active=True,
            shop_id="test_shop",
            demo=True,
            white_list_update_active=False
        )
        user = User(id=1, user_telegram_id=123456789, username="test_user")
        wb_user_cabinet = WBUserCabinet(id=1, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
        wb_token = WBToken(id=1, api_key="test_key", user_id=1, active=True, shop_id="test_shop")
        
        session.add(wb_cabinet)
        session.add(user)
        session.add(wb_user_cabinet)
        session.add(wb_token)
        await session.commit()
        
        # Обновляем объекты и их связи
        await session.refresh(wb_cabinet)
        await session.refresh(user)
        await session.refresh(wb_user_cabinet)
        await session.refresh(wb_token)
        
        # Устанавливаем связи
        wb_user_cabinet.wb_cabinet = wb_cabinet
        wb_user_cabinet.user = user
        wb_token.user = user
        await session.commit()

        mock_bot = AsyncMock()
        mock_state = AsyncMock()
        mock_chat_id = 123456789

        shop_menu = ShopMenu(
            bot=mock_bot,
            chat_id=mock_chat_id,
            state=mock_state,
            wb_user_cabinet_original_id=1
        )

        # Мокаем метод _load_all_data
        async def mock_load_all_data():
            shop_menu._wb_user_cabinet = wb_user_cabinet
            shop_menu._wb_cabinet = wb_cabinet
            shop_menu._balance = 1000.0
            shop_menu._bonus = 100.0
            shop_menu.count_active_advs = 0
            shop_menu.is_active_adv = False
            shop_menu.days_left = 30
            shop_menu.bonus_days = 60
            shop_menu.price_for_month_for_shop = 1000
            shop_menu.total_amount_for_day = 50
            return True

        shop_menu._load_all_data = mock_load_all_data

        result = await shop_menu()
        assert "Test Cabinet" in shop_menu.text
        assert "1000 рублей" in shop_menu.text
        assert "0" in shop_menu.text  # Проверяем количество активных кампаний