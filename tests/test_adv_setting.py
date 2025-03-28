import pytest
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from app.client_bot import const
from unittest.mock import AsyncMock, MagicMock, patch
from tests.mocks import MockAdvSetting, MockWBUserCabinet, MockWBCabinet
from sqlalchemy import select
from sqlalchemy.future import select
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, User, WBToken, AdvSetting
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
def mock_message():
    message = AsyncMock(spec=types.Message)
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.chat = MagicMock()
    message.chat.id = 123456789
    return message

@pytest.fixture
def mock_callback_query():
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.from_user = MagicMock()
    callback.from_user.id = 123456789
    callback.data = "back_to_adv:123"
    callback.message = AsyncMock(spec=types.Message)
    callback.message.chat = MagicMock()
    callback.message.chat.id = 123456789
    return callback

@pytest.fixture
def mock_bot():
    return AsyncMock(spec=Bot)

@pytest.fixture
def mock_state():
    return AsyncMock(spec=FSMContext)

@pytest.fixture
def mock_wb_cabinet():
    return MagicMock(spec=WBCabinet, id=1, shop_id="test_shop")

@pytest.fixture
def mock_user():
    return MagicMock(spec=User, id=1)

@pytest.fixture
def mock_wb_user_cabinet(mock_wb_cabinet, mock_user):
    cabinet = MagicMock(spec=WBUserCabinet)
    cabinet.wb_cabinet = mock_wb_cabinet
    cabinet.user = mock_user
    cabinet.wb_cabinet_id = mock_wb_cabinet.id
    cabinet.user_id = mock_user.id
    return cabinet

@pytest.fixture
def mock_adv_setting():
    return MagicMock(spec=AdvSetting, id=1, name="Test Adv")

@pytest.fixture
def mock_wb_user_cabinet():
    return MagicMock(spec=WBUserCabinet, id=1)

@pytest.mark.asyncio
async def test_create_adv_setting(test_async_db):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time=datetime.now(),
            active=True
        )
        await session.merge(wb_cabinet)
        
        adv_setting = AdvSetting(
            adv_id=123,
            name="test_adv",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True,
            last_update=datetime.now()
        )
        session.add(adv_setting)
        await session.commit()

        # Verify
        result = await session.get(AdvSetting, adv_setting.id)
        assert result is not None
        assert result.adv_id == 123
        assert result.name == "test_adv"

@pytest.mark.asyncio
async def test_update_adv_setting(test_async_db):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time=datetime.now(),
            active=True
        )
        await session.merge(wb_cabinet)
        
        adv_setting = AdvSetting(
            adv_id=123,
            name="test_adv",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True,
            last_update=datetime.now()
        )
        session.add(adv_setting)
        await session.commit()

        # Update
        adv_setting.name = "updated_adv"
        await session.commit()

        # Verify
        result = await session.get(AdvSetting, adv_setting.id)
        assert result.name == "updated_adv"

@pytest.mark.asyncio
async def test_delete_adv_setting(test_async_db):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time=datetime.now(),
            active=True
        )
        await session.merge(wb_cabinet)
        
        adv_setting = AdvSetting(
            adv_id=123,
            name="test_adv",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True,
            last_update=datetime.now()
        )
        session.add(adv_setting)
        await session.commit()

        # Delete
        await session.delete(adv_setting)
        await session.commit()

        # Verify
        result = await session.get(AdvSetting, adv_setting.id)
        assert result is None

@pytest.mark.asyncio
async def test_get_adv_settings_by_cabinet(test_async_db):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time=datetime.now(),
            active=True
        )
        await session.merge(wb_cabinet)
        
        adv_setting1 = AdvSetting(
            adv_id=123,
            name="test_adv1",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True,
            last_update=datetime.now()
        )
        adv_setting2 = AdvSetting(
            adv_id=124,
            name="test_adv2",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True,
            last_update=datetime.now()
        )
        session.add_all([adv_setting1, adv_setting2])
        await session.commit()

        # Query
        stmt = select(AdvSetting).where(AdvSetting.wb_cabinet_id == wb_cabinet.id)
        result = await session.execute(stmt)
        settings = result.scalars().all()

        # Verify
        assert len(settings) == 2
        assert all(s.wb_cabinet_id == wb_cabinet.id for s in settings)

@pytest.mark.asyncio
async def test_adv_setting_relationships(test_async_db):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time=datetime.now(),
            active=True
        )
        await session.merge(wb_cabinet)
        
        adv_setting = AdvSetting(
            adv_id=123,
            name="test_adv",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True,
            last_update=datetime.now()
        )
        session.add(adv_setting)
        await session.commit()

        # Verify relationships
        stmt = select(AdvSetting).where(AdvSetting.id == adv_setting.id)
        result = await session.execute(stmt)
        loaded_setting = result.scalar_one()
        
        assert loaded_setting.wb_cabinet_id == wb_cabinet.id 