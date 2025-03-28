import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, User, WBToken, AdvSetting
from app.modules.shop_runner.shop_data_updater import ShopDataUpdater

@pytest.fixture
def mock_wb_api():
    mock = AsyncMock()
    mock.get_advs.return_value = [
        {"adv_id": 123, "name": "Test Adv 1", "status": "active"},
        {"adv_id": 124, "name": "Test Adv 2", "status": "active"}
    ]
    mock.get_cards.return_value = [
        {"adv_id": 123, "name": "Test Card 1", "status": "active"},
        {"adv_id": 124, "name": "Test Card 2", "status": "active"}
    ]
    return mock

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

@pytest.mark.asyncio
async def test_update_advs_data(test_async_db, mock_wb_api):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time="2024-01-01",
            active=True
        )
        await session.merge(wb_cabinet)
        
        # Create ShopDataUpdater instance
        updater = ShopDataUpdater(wb_cabinet.id, mock_wb_api, session)
        
        # Update data
        await updater.update_advs_data()
        
        # Verify
        from sqlalchemy import select
        stmt = select(AdvSetting).where(AdvSetting.wb_cabinet_id == wb_cabinet.id)
        result = await session.execute(stmt)
        settings = result.scalars().all()
        
        assert len(settings) == 2
        assert all(s.wb_cabinet_id == wb_cabinet.id for s in settings)

@pytest.mark.asyncio
async def test_update_cards_data(test_async_db, mock_wb_api):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time="2024-01-01",
            active=True
        )
        await session.merge(wb_cabinet)
        
        # Create ShopDataUpdater instance
        updater = ShopDataUpdater(wb_cabinet.id, mock_wb_api, session)
        
        # Update data
        await updater.update_cards_data()
        
        # Verify
        from sqlalchemy import select
        stmt = select(AdvSetting).where(AdvSetting.wb_cabinet_id == wb_cabinet.id)
        result = await session.execute(stmt)
        settings = result.scalars().all()
        
        assert len(settings) == 2
        assert all(s.wb_cabinet_id == wb_cabinet.id for s in settings)

@pytest.mark.asyncio
async def test_update_all_data(test_async_db, mock_wb_api):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time="2024-01-01",
            active=True
        )
        await session.merge(wb_cabinet)
        
        # Create ShopDataUpdater instance
        updater = ShopDataUpdater(wb_cabinet.id, mock_wb_api, session)
        
        # Update all data
        await updater.update_all_data()
        
        # Verify
        from sqlalchemy import select
        stmt = select(AdvSetting).where(AdvSetting.wb_cabinet_id == wb_cabinet.id)
        result = await session.execute(stmt)
        settings = result.scalars().all()
        
        assert len(settings) == 4  # 2 advs + 2 cards
        assert all(s.wb_cabinet_id == wb_cabinet.id for s in settings)

@pytest.mark.asyncio
async def test_update_all_data_with_error(test_async_db, mock_wb_api):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time="2024-01-01",
            active=True
        )
        await session.merge(wb_cabinet)
        
        # Create ShopDataUpdater instance with error-raising mock
        mock_wb_api.get_advs.side_effect = Exception("API Error")
        updater = ShopDataUpdater(wb_cabinet.id, mock_wb_api, session)
        
        # Update should raise exception
        with pytest.raises(Exception) as exc_info:
            await updater.update_all_data()
        
        assert str(exc_info.value) == "API Error" 