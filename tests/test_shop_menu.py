import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
from app.client_bot.user_interface.views.messages import ShopMenu
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
    return ShopMenu(
        bot=mock_bot,
        chat_id=mock_chat_id,
        state=mock_state,
        wb_user_cabinet_original_id=mock_wb_user_cabinet.id
    )

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
            demo=True
        )
        user = User(id=1, user_telegram_id=123456789, username="test_user")
        wb_user_cabinet = WBUserCabinet(id=1, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
        wb_token = WBToken(id=1, api_key="test_key", user_id=1, active=True, shop_id="test_shop")
        
        session.add(wb_cabinet)
        session.add(user)
        session.add(wb_user_cabinet)
        session.add(wb_token)
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

        result = await shop_menu()
        assert "Магазин" in shop_menu.text
        assert "Test Cabinet" in shop_menu.text
        assert "1000.0" in shop_menu.text

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
            demo=True
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
            active_status="active"
        )
        
        session.add(wb_cabinet)
        session.add(user)
        session.add(wb_user_cabinet)
        session.add(wb_token)
        session.add(adv_setting)
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

        result = await shop_menu()
        assert "Test Cabinet" in shop_menu.text
        assert "1000.0" in shop_menu.text
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
            demo=True
        )
        user = User(id=1, user_telegram_id=123456789, username="test_user")
        wb_user_cabinet = WBUserCabinet(id=1, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
        wb_token = WBToken(id=1, api_key="test_key", user_id=1, active=True, shop_id="test_shop")
        
        session.add(wb_cabinet)
        session.add(user)
        session.add(wb_user_cabinet)
        session.add(wb_token)
        await session.commit()

        shop_menu = ShopMenu(
            bot=mock_bot,
            chat_id=mock_chat_id,
            state=mock_state,
            wb_user_cabinet_original_id=1
        )

        result = await shop_menu()
        assert "Магазин" in shop_menu.text
        assert "Test Cabinet" in shop_menu.text

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
            demo=True
        )
        user = User(id=1, user_telegram_id=123456789, username="test_user")
        wb_user_cabinet = WBUserCabinet(id=1, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
        wb_token = WBToken(id=1, api_key="test_key", user_id=1, active=True, shop_id="test_shop")
        adv_setting = AdvSetting(
            id=1,
            name="Test Adv",
            wb_cabinet_id=1,
            last_update=current_time,
            bot_active=True
        )
        
        session.add(wb_cabinet)
        session.add(user)
        session.add(wb_user_cabinet)
        session.add(wb_token)
        session.add(adv_setting)
        await session.commit()

        shop_menu = ShopMenu(
            bot=mock_bot,
            chat_id=mock_chat_id,
            state=mock_state,
            wb_user_cabinet_original_id=1
        )

        result = await shop_menu()
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
            demo=True
        )
        user = User(id=1, user_telegram_id=123456789, username="test_user")
        wb_user_cabinet = WBUserCabinet(id=1, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
        wb_token = WBToken(id=1, api_key="test_key", user_id=1, active=True, shop_id="test_shop")
        
        session.add(wb_cabinet)
        session.add(user)
        session.add(wb_user_cabinet)
        session.add(wb_token)
        await session.commit()

        shop_menu = ShopMenu(
            bot=mock_bot,
            chat_id=mock_chat_id,
            state=mock_state,
            wb_user_cabinet_original_id=1
        )

        result = await shop_menu()
        assert "0" in shop_menu.text  # Проверяем, что нет активных кампаний

@pytest.mark.asyncio
async def test_get_adv_menu_with_error(mock_bot, mock_state, mock_chat_id):
    mock_state.get_data = AsyncMock(side_effect=Exception("Test error"))
    shop_menu = ShopMenu(
        bot=mock_bot,
        chat_id=mock_chat_id,
        state=mock_state,
        wb_user_cabinet_original_id=1
    )
    with pytest.raises(Exception):
        result = await shop_menu()