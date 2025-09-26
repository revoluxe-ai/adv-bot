"""Tests for PromotionManager class."""

import pytest
from unittest.mock import AsyncMock, Mock

from app.core.mp.wb.promotion_manager import PromotionManager
from app.core.mp.wb.factories.adapter_factory import WbApiAdapterFactory


class TestPromotionManager:
    """Test cases for PromotionManager delegation to adapters."""

    @pytest.fixture
    def mock_adapter_factory(self):
        """Create a mock adapter factory."""
        return Mock(spec=WbApiAdapterFactory)

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock adapter with async methods."""
        adapter = Mock()
        adapter.get_min_bids = AsyncMock(return_value={123: 50, 456: 75})
        adapter.get_current_bids = AsyncMock(return_value={123: 60, 456: 80})
        adapter.update_bids = AsyncMock()
        return adapter

    @pytest.fixture
    def promotion_manager(self, mock_adapter_factory):
        """Create PromotionManager instance with mocked factory."""
        return PromotionManager(mock_adapter_factory)

    @pytest.mark.asyncio
    async def test_get_min_bids_delegates_to_adapter(
        self, promotion_manager, mock_adapter_factory, mock_adapter
    ):
        """Test that get_min_bids correctly delegates to adapter."""
        # Arrange
        mock_adapter_factory.get_adapter.return_value = mock_adapter
        shop_id = "test_shop"
        adv_id = 123
        nmids = [111, 222]
        expected_result = {111: 30, 222: 40}
        mock_adapter.get_min_bids.return_value = expected_result

        # Act
        result = await promotion_manager.get_min_bids(shop_id, adv_id=adv_id, nmids=nmids)

        # Assert
        mock_adapter_factory.get_adapter.assert_called_once_with(
            shop_id, section="promotion", version="v1"
        )
        mock_adapter.get_min_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_get_current_bids_delegates_to_adapter(
        self, promotion_manager, mock_adapter_factory, mock_adapter
    ):
        """Test that get_current_bids correctly delegates to adapter."""
        # Arrange
        mock_adapter_factory.get_adapter.return_value = mock_adapter
        shop_id = "test_shop"
        adv_id = 456
        nmids = [333, 444]
        expected_result = {333: 55, 444: 65}
        mock_adapter.get_current_bids.return_value = expected_result

        # Act
        result = await promotion_manager.get_current_bids(shop_id, adv_id=adv_id, nmids=nmids)

        # Assert
        mock_adapter_factory.get_adapter.assert_called_once_with(
            shop_id, section="promotion", version="v1"
        )
        mock_adapter.get_current_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_update_bids_delegates_to_adapter(
        self, promotion_manager, mock_adapter_factory, mock_adapter
    ):
        """Test that update_bids correctly delegates to adapter."""
        # Arrange
        mock_adapter_factory.get_adapter.return_value = mock_adapter
        shop_id = "test_shop"
        adv_id = 789
        nmids_bids = [{"nmid": 555, "cpm": 100}, {"nmid": 666, "cpm": 120}]

        # Act
        await promotion_manager.update_bids(shop_id, adv_id=adv_id, nm_bids=nmids_bids)

        # Assert
        mock_adapter_factory.get_adapter.assert_called_once_with(
            shop_id, section="promotion", version="v1"
        )
        mock_adapter.update_bids.assert_called_once_with(shop_id, adv_id=adv_id, nm_bids=nmids_bids)

    @pytest.mark.asyncio
    async def test_adapter_factory_called_with_correct_parameters(
        self, promotion_manager, mock_adapter_factory, mock_adapter
    ):
        """Test that adapter factory is always called with promotion/v1 parameters."""
        # Arrange
        mock_adapter_factory.get_adapter.return_value = mock_adapter
        shop_id = "different_shop"

        # Act - call all methods
        await promotion_manager.get_min_bids(shop_id, adv_id=1, nmids=[1])
        await promotion_manager.get_current_bids(shop_id, adv_id=2, nmids=[2])
        await promotion_manager.update_bids(shop_id, adv_id=3, nm_bids=[])

        # Assert - all calls should use same section/version
        assert len(mock_adapter_factory.get_adapter.call_args_list) == 3
        
        for call in mock_adapter_factory.get_adapter.call_args_list:
            # Check that get_adapter was called with correct parameters
            assert call[0] == (shop_id,)  # positional args
            assert call[1] == {"section": "promotion", "version": "v1"}  # keyword args

    def test_promotion_manager_initialization(self, mock_adapter_factory):
        """Test that PromotionManager initializes correctly with adapter factory."""
        # Act
        manager = PromotionManager(mock_adapter_factory)

        # Assert
        assert manager._adapter_factory is mock_adapter_factory

    @pytest.mark.asyncio
    async def test_adapter_exceptions_are_propagated(
        self, promotion_manager, mock_adapter_factory, mock_adapter
    ):
        """Test that exceptions from adapters are properly propagated."""
        # Arrange
        mock_adapter_factory.get_adapter.return_value = mock_adapter
        expected_exception = RuntimeError("Adapter error")
        mock_adapter.get_min_bids.side_effect = expected_exception

        # Act & Assert
        with pytest.raises(RuntimeError, match="Adapter error"):
            await promotion_manager.get_min_bids("shop", adv_id=1, nmids=[1])