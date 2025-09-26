"""Tests for PromotionBidsService."""

import time
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.mp.wb.promotion_manager import PromotionManager
from app.core.mp.wb.services.promotion_bids_service import PromotionBidsService


class TestPromotionBidsService:
    """Test cases for PromotionBidsService."""

    @pytest.fixture
    def mock_promotion_manager(self):
        """Create a mock PromotionManager."""
        manager = Mock(spec=PromotionManager)
        manager.get_min_bids = AsyncMock(return_value={123: 10, 456: 15})
        manager.get_current_bids = AsyncMock(return_value={123: 20, 456: 25})
        manager.update_bids = AsyncMock()
        return manager

    @pytest.fixture
    def promotion_bids_service(self, mock_promotion_manager):
        """Create PromotionBidsService with mocked PromotionManager."""
        return PromotionBidsService(mock_promotion_manager)

    def test_initialization(self, mock_promotion_manager):
        service = PromotionBidsService(mock_promotion_manager)
        assert service._promotion_manager is mock_promotion_manager

    @pytest.mark.asyncio
    async def test_resolve_min_bids_success(self, promotion_bids_service, mock_promotion_manager):
        shop_id, adv_id, nmids = "test_shop", 100, [123, 456]
        expected_result = {123: 10, 456: 15}
        mock_promotion_manager.get_min_bids.return_value = expected_result

        result = await promotion_bids_service.resolve_min_bids(shop_id, adv_id, nmids)

        mock_promotion_manager.get_min_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_resolve_min_bids_error(self, promotion_bids_service, mock_promotion_manager):
        shop_id, adv_id, nmids = "test_shop", 100, [123, 456]
        mock_promotion_manager.get_min_bids.side_effect = RuntimeError("API Error")

        with pytest.raises(RuntimeError, match="API Error"):
            await promotion_bids_service.resolve_min_bids(shop_id, adv_id, nmids)

    @pytest.mark.asyncio
    async def test_resolve_current_bids_success(self, promotion_bids_service, mock_promotion_manager):
        shop_id, adv_id, nmids = "test_shop", 100, [123, 456]
        expected_result = {123: 20, 456: 25}
        mock_promotion_manager.get_current_bids.return_value = expected_result

        result = await promotion_bids_service.resolve_current_bids(shop_id, adv_id, nmids)

        mock_promotion_manager.get_current_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_resolve_current_bids_error(self, promotion_bids_service, mock_promotion_manager):
        shop_id, adv_id, nmids = "test_shop", 100, [123, 456]
        mock_promotion_manager.get_current_bids.side_effect = RuntimeError("API Error")

        with pytest.raises(RuntimeError, match="API Error"):
            await promotion_bids_service.resolve_current_bids(shop_id, adv_id, nmids)

    @pytest.mark.asyncio
    async def test_update_bids_success(self, promotion_bids_service, mock_promotion_manager):
        shop_id, adv_id = "test_shop", 100
        nmid_bids = [{"nmid": 123, "cpm": 30}, {"nmid": 456, "cpm": 35}]

        await promotion_bids_service.update_bids(shop_id, adv_id, nm_bids)

        mock_promotion_manager.update_bids.assert_called_once_with(shop_id, adv_id=adv_id, nm_bids=nm_bids)

    @pytest.mark.asyncio
    async def test_update_bids_error(self, promotion_bids_service, mock_promotion_manager):
        shop_id, adv_id = "test_shop", 100
        nmids_bids = [{"nmid": 123, "cpm": 30}]
        mock_promotion_manager.update_bids.side_effect = RuntimeError("Update Error")

        with pytest.raises(RuntimeError, match="Update Error"):
            await promotion_bids_service.update_bids(shop_id, adv_id, nm_bids)

    @pytest.mark.asyncio
    async def test_resolve_min_bids_with_empty_nmids(self, promotion_bids_service, mock_promotion_manager):
        shop_id, adv_id, nmids = "test_shop", 100, []
        mock_promotion_manager.get_min_bids.return_value = {}

        result = await promotion_bids_service.resolve_min_bids(shop_id, adv_id, nmids)

        mock_promotion_manager.get_min_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        assert result == {}

    @pytest.mark.asyncio
    async def test_service_delegates_correctly(self, promotion_bids_service, mock_promotion_manager):
        shop_id, adv_id, nmids = "test_shop", 100, [123, 456]
        nmis_bids = [{"nmid": 123, "cpm": 30}]

        mock_promotion_manager.get_min_bids.return_value = {123: 10}
        mock_promotion_manager.get_current_bids.return_value = {123: 20}

      