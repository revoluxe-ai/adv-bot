"""Tests for PromotionBidsService."""

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
        """Test that PromotionBidsService initializes correctly."""
        # Act
        service = PromotionBidsService(mock_promotion_manager)

        # Assert
        assert service._promotion_manager is mock_promotion_manager

    @pytest.mark.asyncio
    async def test_resolve_min_bids_success(self, promotion_bids_service, mock_promotion_manager):
        """Test successful resolve_min_bids."""
        # Arrange
        shop_id = "test_shop"
        adv_id = 100
        nmids = [123, 456]
        expected_result = {123: 10, 456: 15}
        mock_promotion_manager.get_min_bids.return_value = expected_result

        # Act
        result = await promotion_bids_service.resolve_min_bids(shop_id, adv_id, nmids)

        # Assert
        mock_promotion_manager.get_min_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_resolve_min_bids_error(self, promotion_bids_service, mock_promotion_manager):
        """Test resolve_min_bids error handling."""
        # Arrange
        shop_id = "test_shop"
        adv_id = 100
        nmids = [123, 456]
        expected_error = RuntimeError("API Error")
        mock_promotion_manager.get_min_bids.side_effect = expected_error

        # Act & Assert
        with pytest.raises(RuntimeError, match="API Error"):
            await promotion_bids_service.resolve_min_bids(shop_id, adv_id, nmids)

    @pytest.mark.asyncio
    async def test_resolve_current_bids_success(self, promotion_bids_service, mock_promotion_manager):
        """Test successful resolve_current_bids."""
        # Arrange
        shop_id = "test_shop"
        adv_id = 100
        nmids = [123, 456]
        expected_result = {123: 20, 456: 25}
        mock_promotion_manager.get_current_bids.return_value = expected_result

        # Act
        result = await promotion_bids_service.resolve_current_bids(shop_id, adv_id, nmids)

        # Assert
        mock_promotion_manager.get_current_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_resolve_current_bids_error(self, promotion_bids_service, mock_promotion_manager):
        """Test resolve_current_bids error handling."""
        # Arrange
        shop_id = "test_shop"
        adv_id = 100
        nmids = [123, 456]
        expected_error = RuntimeError("API Error")
        mock_promotion_manager.get_current_bids.side_effect = expected_error

        # Act & Assert
        with pytest.raises(RuntimeError, match="API Error"):
            await promotion_bids_service.resolve_current_bids(shop_id, adv_id, nmids)

    @pytest.mark.asyncio
    async def test_update_bids_success(self, promotion_bids_service, mock_promotion_manager):
        """Test successful update_bids."""
        # Arrange
        shop_id = "test_shop"
        adv_id = 100
        nm_bids = [{"nm": 123, "cpm": 30}, {"nm": 456, "cpm": 35}]

        # Act
        await promotion_bids_service.update_bids(shop_id, adv_id, nm_bids)

        # Assert
        mock_promotion_manager.update_bids.assert_called_once_with(shop_id, adv_id=adv_id, nm_bids=nm_bids)

    @pytest.mark.asyncio
    async def test_update_bids_error(self, promotion_bids_service, mock_promotion_manager):
        """Test update_bids error handling."""
        # Arrange
        shop_id = "test_shop"
        adv_id = 100
        nm_bids = [{"nm": 123, "cpm": 30}]
        expected_error = RuntimeError("Update Error")
        mock_promotion_manager.update_bids.side_effect = expected_error

        # Act & Assert
        with pytest.raises(RuntimeError, match="Update Error"):
            await promotion_bids_service.update_bids(shop_id, adv_id, nm_bids)

    @pytest.mark.asyncio
    async def test_resolve_min_bids_with_empty_nmids(self, promotion_bids_service, mock_promotion_manager):
        """Test resolve_min_bids with empty nmids list."""
        # Arrange
        shop_id = "test_shop"
        adv_id = 100
        nmids = []
        mock_promotion_manager.get_min_bids.return_value = {}

        # Act
        result = await promotion_bids_service.resolve_min_bids(shop_id, adv_id, nmids)

        # Assert
        mock_promotion_manager.get_min_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        assert result == {}

    @pytest.mark.asyncio
    async def test_service_delegates_correctly(self, promotion_bids_service, mock_promotion_manager):
        """Test that service correctly delegates all operations to PromotionManager."""
        # Arrange
        shop_id = "test_shop"
        adv_id = 100
        nmids = [123, 456]
        nm_bids = [{"nm": 123, "cpm": 30}]

        mock_promotion_manager.get_min_bids.return_value = {123: 10}
        mock_promotion_manager.get_current_bids.return_value = {123: 20}

        # Act - call all methods
        min_result = await promotion_bids_service.resolve_min_bids(shop_id, adv_id, nmids)
        current_result = await promotion_bids_service.resolve_current_bids(shop_id, adv_id, nmids)
        await promotion_bids_service.update_bids(shop_id, adv_id, nm_bids)

        # Assert - all methods called PromotionManager correctly
        mock_promotion_manager.get_min_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        mock_promotion_manager.get_current_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        mock_promotion_manager.update_bids.assert_called_once_with(shop_id, adv_id=adv_id, nm_bids=nm_bids)

        assert min_result == {123: 10}
        assert current_result == {123: 20}
