"""Tests for PromotionBidsService."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.mp.wb.containers import WBApiContainer
from app.core.mp.wb.managers.promotion import PromotionManager
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

        # Test all three delegated methods
        min_bids = await promotion_bids_service.resolve_min_bids(shop_id, adv_id, nmids)
        current_bids = await promotion_bids_service.resolve_current_bids(shop_id, adv_id, nmids)
        await promotion_bids_service.update_bids(shop_id, adv_id, nm_bids)

        # Verify all calls were made correctly
        mock_promotion_manager.get_min_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        mock_promotion_manager.get_current_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        mock_promotion_manager.update_bids.assert_called_once_with(shop_id, adv_id=adv_id, nm_bids=nm_bids)

        assert min_bids == {123: 10}
        assert current_bids == {123: 20}


class TestPromotionBidsServiceIntegration:
    """Integration tests for PromotionBidsService using DI container with mocked dependencies."""

    @pytest.fixture
    def mock_adapter_factory(self):
        """Create a mock WbApiAdapterFactory."""
        factory = Mock()
        
        # Create mock adapter with async methods
        mock_adapter = Mock()
        mock_adapter.get_min_bids = AsyncMock(return_value={123: 10, 456: 15})
        mock_adapter.get_current_bids = AsyncMock(return_value={123: 20, 456: 25})
        mock_adapter.update_bids = AsyncMock()
        
        factory.get_adapter.return_value = mock_adapter
        return factory, mock_adapter

    @pytest.fixture
    def di_container_with_mocks(self, mock_adapter_factory):
        """Create DI container with mocked dependencies to avoid real API calls."""
        container = WBApiContainer()
        
        # Override the adapter factory with our mock
        factory_mock, adapter_mock = mock_adapter_factory
        container.wb_api_adapter_factory.override(factory_mock)
        
        return container, adapter_mock

    @pytest.mark.asyncio
    async def test_di_integration_resolve_min_bids(self, di_container_with_mocks):
        """Test resolve_min_bids through DI container with mocked adapter."""
        container, mock_adapter = di_container_with_mocks
        
        # Get service from DI container
        service = container.promotion_bids_service()
        
        shop_id, adv_id, nmids = "test_shop", 100, [123, 456]
        expected_result = {123: 10, 456: 15}
        mock_adapter.get_min_bids.return_value = expected_result
        
        result = await service.resolve_min_bids(shop_id, adv_id, nmids)
        
        # Verify adapter was called correctly
        mock_adapter.get_min_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_di_integration_resolve_current_bids(self, di_container_with_mocks):
        """Test resolve_current_bids through DI container with mocked adapter."""
        container, mock_adapter = di_container_with_mocks
        
        service = container.promotion_bids_service()
        
        shop_id, adv_id, nmids = "test_shop", 100, [123, 456]
        expected_result = {123: 20, 456: 25}
        mock_adapter.get_current_bids.return_value = expected_result
        
        result = await service.resolve_current_bids(shop_id, adv_id, nmids)
        
        mock_adapter.get_current_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_di_integration_update_bids(self, di_container_with_mocks):
        """Test update_bids through DI container with mocked adapter."""
        container, mock_adapter = di_container_with_mocks
        
        service = container.promotion_bids_service()
        
        shop_id, adv_id = "test_shop", 100
        nm_bids = [{"nm": 123, "cpm": 30}, {"nm": 456, "cpm": 35}]
        
        await service.update_bids(shop_id, adv_id, nm_bids)
        
        mock_adapter.update_bids.assert_called_once_with(shop_id, adv_id=adv_id, nm_bids=nm_bids)

    @pytest.mark.asyncio
    async def test_di_integration_service_singleton(self, di_container_with_mocks):
        """Test that PromotionBidsService is properly configured as singleton in DI."""
        container, _ = di_container_with_mocks
        
        # Get service twice and verify it's the same instance (singleton)
        service1 = container.promotion_bids_service()
        service2 = container.promotion_bids_service()
        
        assert service1 is service2
        assert isinstance(service1, PromotionBidsService)
        assert isinstance(service2, PromotionBidsService)

    @pytest.mark.asyncio
    async def test_di_integration_full_workflow(self, di_container_with_mocks):
        """Test complete workflow: get min bids, get current bids, then update."""
        container, mock_adapter = di_container_with_mocks
        
        service = container.promotion_bids_service()
        
        shop_id, adv_id, nmids = "test_shop", 100, [123, 456]
        
        # Setup mock responses
        mock_adapter.get_min_bids.return_value = {123: 10, 456: 15}
        mock_adapter.get_current_bids.return_value = {123: 20, 456: 25}
        
        # Execute full workflow
        min_bids = await service.resolve_min_bids(shop_id, adv_id, nmids)
        current_bids = await service.resolve_current_bids(shop_id, adv_id, nmids)
        
        # Calculate new bids (example logic)
        new_bids = [{"nm": nm, "cpm": min_bids[nm] + 5} for nm in nmids]
        await service.update_bids(shop_id, adv_id, new_bids)
        
        # Verify all operations
        assert min_bids == {123: 10, 456: 15}
        assert current_bids == {123: 20, 456: 25}
        
        mock_adapter.get_min_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        mock_adapter.get_current_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)
        mock_adapter.update_bids.assert_called_once_with(shop_id, adv_id=adv_id, nm_bids=new_bids)

    @pytest.mark.asyncio
    async def test_di_integration_concurrent_operations(self, di_container_with_mocks):
        """Test concurrent operations through DI container."""
        container, mock_adapter = di_container_with_mocks
        
        service = container.promotion_bids_service()
        
        shop_id, adv_id, nmids = "test_shop", 100, [123, 456]
        
        # Setup mock responses with delays to simulate real API
        async def delayed_min_bids(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {123: 10, 456: 15}
            
        async def delayed_current_bids(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {123: 20, 456: 25}
        
        mock_adapter.get_min_bids.side_effect = delayed_min_bids
        mock_adapter.get_current_bids.side_effect = delayed_current_bids
        
        # Execute concurrent operations
        start_time = time.time()
        min_bids_task = asyncio.create_task(service.resolve_min_bids(shop_id, adv_id, nmids))
        current_bids_task = asyncio.create_task(service.resolve_current_bids(shop_id, adv_id, nmids))
        
        min_bids, current_bids = await asyncio.gather(min_bids_task, current_bids_task)
        elapsed_time = time.time() - start_time
        
        # Verify results and that operations ran concurrently (less than 0.2s total)
        assert min_bids == {123: 10, 456: 15}
        assert current_bids == {123: 20, 456: 25}
        assert elapsed_time < 0.2  # Should be around 0.1s if concurrent
        
        # Verify both methods were called
        mock_adapter.get_min_bids.assert_called_once()
        mock_adapter.get_current_bids.assert_called_once()

    @pytest.mark.asyncio
    async def test_di_integration_error_handling(self, di_container_with_mocks):
        """Test error handling through DI container."""
        container, mock_adapter = di_container_with_mocks
        
        service = container.promotion_bids_service()
        
        shop_id, adv_id, nmids = "test_shop", 100, [123, 456]
        
        # Setup mock to raise error
        mock_adapter.get_min_bids.side_effect = RuntimeError("API connection failed")
        
        # Verify error propagates correctly
        with pytest.raises(RuntimeError, match="API connection failed"):
            await service.resolve_min_bids(shop_id, adv_id, nmids)
        
        mock_adapter.get_min_bids.assert_called_once_with(shop_id, adv_id=adv_id, nmids=nmids)

    @pytest.mark.asyncio
    async def test_di_integration_container_cleanup(self, di_container_with_mocks):
        """Test proper cleanup of DI container resources."""
        container, mock_adapter = di_container_with_mocks
        
        service = container.promotion_bids_service()
        
        # Use service
        await service.resolve_min_bids("test_shop", 100, [123])
        
        # Reset container (simulate cleanup)
        container.reset_singletons()
        
        # Get new service instance after reset
        new_service = container.promotion_bids_service()
        
        # Should be different instance after reset
        assert new_service is not service
        assert isinstance(new_service, PromotionBidsService)


