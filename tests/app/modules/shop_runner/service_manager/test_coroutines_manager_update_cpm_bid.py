"""
Unit tests for CoroutinesManager.update_cpm_bid_in_search_advs method.

Tests cover the business logic, error handling, and edge cases for the method
that manages CPM bid updates in search advertisements.
"""

import asyncio
from collections.abc import Awaitable
from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager.manager import CoroutinesManager
from app.modules.shop_runner.service_manager.wb_shop_data_manager import WBShopDataManager


@pytest.fixture
def mock_wb_cabinet():
    """Mock WBCabinet for testing."""
    cabinet = Mock()
    cabinet.shop_id = "test_shop_123"
    cabinet.id = 1
    return cabinet


@pytest.fixture
def mock_wb_api(mock_wb_cabinet):
    """Mock WBApi for testing."""
    api = Mock()
    api.wb_cabinet = mock_wb_cabinet
    api.shop_id = "test_shop_123"
    api.session = AsyncMock()
    return api


@pytest.fixture
def mock_adv_setting():
    """Mock AdvSetting for testing."""
    adv = Mock()
    adv.id = 1
    adv.adv_id = 100
    adv.search_adv_id = 200
    adv.name = "Test Campaign"
    adv.max_cpm = 50
    adv.max_place = 5
    adv.nmids = [12345, 67890]
    adv.bot_active = True
    return adv


@pytest.fixture
def mock_calculated_keyword():
    """Mock CalculatedKeyword for testing."""
    keyword = Mock()
    keyword.text = "test keyword"
    keyword.keyword_setting_original_id = "1"
    keyword.rating_by_predict_ctr = 0.5
    keyword.predict_ctr = 0.1
    return keyword


@pytest.fixture
def coroutines_manager(mock_wb_api):
    """Create CoroutinesManager instance for testing."""
    return CoroutinesManager(mock_wb_api)


class TestCoroutinesManagerUpdateCpmBidInSearchAdvs:
    """Test suite for CoroutinesManager.update_cpm_bid_in_search_advs method."""

    @pytest.mark.asyncio
    async def test_successful_execution_with_active_advs(
        self, coroutines_manager, mock_adv_setting, mock_calculated_keyword
    ):
        """Test successful execution when active advertisements exist."""
        # Arrange
        mock_keywords = [mock_calculated_keyword]
        adv_settings = [mock_adv_setting]

        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager._wb_shop_data_manager,
                "get_calculated_keywords",
                return_value=asyncio.create_task(asyncio.sleep(0, result=mock_keywords)),
            ) as mock_get_keywords:
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock()
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act
                    result = await coroutines_manager.update_cpm_bid_in_search_advs()

                    # Assert
                    assert result is None
                    mock_get_active_advs.assert_called_once()
                    mock_get_keywords.assert_called_once_with(mock_adv_setting)
                    mock_update_cpm_manager_class.assert_called_once_with("test_shop_123")
                    mock_update_cpm_manager.update_cpms_in_search_advs.assert_called_once()

                    # Verify the structure of adv_keywords_coro passed to UpdateCPMManager
                    call_args = mock_update_cpm_manager.update_cpms_in_search_advs.call_args[0][0]
                    assert len(call_args) == 1
                    assert call_args[0][0] == mock_adv_setting
                    assert isinstance(call_args[0][1], asyncio.Task)

    @pytest.mark.asyncio
    async def test_early_return_when_no_active_advs(self, coroutines_manager):
        """Test early return when no active advertisements exist."""
        # Arrange
        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = []

            with patch(
                "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
            ) as mock_update_cpm_manager_class:
                # Act
                result = await coroutines_manager.update_cpm_bid_in_search_advs()

                # Assert
                assert result is None
                mock_get_active_advs.assert_called_once()
                mock_update_cpm_manager_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_early_return_when_none_active_advs(self, coroutines_manager):
        """Test early return when get_active_advs returns None."""
        # Arrange
        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = None

            with patch(
                "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
            ) as mock_update_cpm_manager_class:
                # Act
                result = await coroutines_manager.update_cpm_bid_in_search_advs()

                # Assert
                assert result is None
                mock_get_active_advs.assert_called_once()
                mock_update_cpm_manager_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_advs_processing(self, coroutines_manager):
        """Test processing multiple advertisements."""
        # Arrange
        adv1 = Mock(spec=AdvSetting)
        adv1.id = 1
        adv1.name = "Campaign 1"

        adv2 = Mock(spec=AdvSetting)
        adv2.id = 2
        adv2.name = "Campaign 2"

        adv_settings = [adv1, adv2]

        mock_keywords1 = [Mock(spec=CalculatedKeyword)]
        mock_keywords2 = [Mock(spec=CalculatedKeyword)]

        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            async def mock_get_keywords_side_effect(adv):
                if adv == adv1:
                    return mock_keywords1
                elif adv == adv2:
                    return mock_keywords2
                return []

            with patch.object(
                coroutines_manager._wb_shop_data_manager,
                "get_calculated_keywords",
                side_effect=lambda adv: asyncio.create_task(mock_get_keywords_side_effect(adv)),
            ) as mock_get_keywords:
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock()
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act
                    result = await coroutines_manager.update_cpm_bid_in_search_advs()

                    # Assert
                    assert result is None
                    mock_get_active_advs.assert_called_once()
                    assert mock_get_keywords.call_count == 2
                    mock_get_keywords.assert_any_call(adv1)
                    mock_get_keywords.assert_any_call(adv2)

                    # Verify the adv_keywords_coro structure
                    call_args = mock_update_cpm_manager.update_cpms_in_search_advs.call_args[0][0]
                    assert len(call_args) == 2
                    assert call_args[0][0] == adv1
                    assert call_args[1][0] == adv2
                    assert isinstance(call_args[0][1], asyncio.Task)
                    assert isinstance(call_args[1][1], asyncio.Task)

    @pytest.mark.asyncio
    async def test_error_handling_in_get_active_advs(self, coroutines_manager):
        """Test error handling when get_active_advs raises an exception."""
        # Arrange
        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.side_effect = Exception("Database error")

            # Act & Assert
            with pytest.raises(Exception, match="Database error"):
                await coroutines_manager.update_cpm_bid_in_search_advs()

    @pytest.mark.asyncio
    async def test_error_handling_in_update_cpm_manager(self, coroutines_manager, mock_adv_setting):
        """Test error handling when UpdateCPMManager raises an exception."""
        # Arrange
        adv_settings = [mock_adv_setting]
        mock_keywords = [Mock(spec=CalculatedKeyword)]

        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager._wb_shop_data_manager,
                "get_calculated_keywords",
                return_value=asyncio.create_task(asyncio.sleep(0, result=mock_keywords)),
            ):
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock(
                        side_effect=Exception("UpdateCPM error")
                    )
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act & Assert
                    with pytest.raises(Exception, match="UpdateCPM error"):
                        await coroutines_manager.update_cpm_bid_in_search_advs()

    @pytest.mark.asyncio
    async def test_shop_id_passed_correctly_to_update_cpm_manager(self, coroutines_manager, mock_adv_setting):
        """Test that shop_id is correctly passed to UpdateCPMManager constructor."""
        # Arrange
        adv_settings = [mock_adv_setting]
        mock_keywords = [Mock(spec=CalculatedKeyword)]

        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager._wb_shop_data_manager,
                "get_calculated_keywords",
                return_value=asyncio.create_task(asyncio.sleep(0, result=mock_keywords)),
            ):
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock()
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act
                    await coroutines_manager.update_cpm_bid_in_search_advs()

                    # Assert
                    mock_update_cpm_manager_class.assert_called_once_with("test_shop_123")

    @pytest.mark.asyncio
    async def test_method_returns_none_consistently(self, coroutines_manager):
        """Test that method always returns None regardless of execution path."""
        # Test case 1: No active advs
        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = []
            result = await coroutines_manager.update_cpm_bid_in_search_advs()
            assert result is None

        # Test case 2: With active advs
        mock_adv = Mock(spec=AdvSetting)
        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = [mock_adv]

            with patch.object(
                coroutines_manager._wb_shop_data_manager,
                "get_calculated_keywords",
                return_value=asyncio.create_task(asyncio.sleep(0, result=[])),
            ):
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock()
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    result = await coroutines_manager.update_cpm_bid_in_search_advs()
                    assert result is None

    @pytest.mark.asyncio
    async def test_wb_shop_data_manager_dependency_injection(self, mock_wb_api, mock_wb_cabinet):
        """Test that WBShopDataManager is properly initialized with wb_cabinet."""
        # Arrange & Act
        manager = CoroutinesManager(mock_wb_api)

        # Assert
        assert manager._wb_shop_data_manager is not None
        assert isinstance(manager._wb_shop_data_manager, WBShopDataManager)
        assert manager.shop_id == "test_shop_123"

    @pytest.mark.asyncio
    async def test_get_calculated_keywords_called_for_each_adv(self, coroutines_manager):
        """Test that get_calculated_keywords is called for each advertisement."""
        # Arrange
        adv1 = Mock(spec=AdvSetting, id=1, name="Campaign 1")
        adv2 = Mock(spec=AdvSetting, id=2, name="Campaign 2")
        adv3 = Mock(spec=AdvSetting, id=3, name="Campaign 3")
        adv_settings = [adv1, adv2, adv3]

        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager._wb_shop_data_manager,
                "get_calculated_keywords",
                return_value=asyncio.create_task(asyncio.sleep(0, result=[])),
            ) as mock_get_keywords:
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock()
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act
                    await coroutines_manager.update_cpm_bid_in_search_advs()

                    # Assert
                    assert mock_get_keywords.call_count == 3
                    mock_get_keywords.assert_any_call(adv1)
                    mock_get_keywords.assert_any_call(adv2)
                    mock_get_keywords.assert_any_call(adv3)

    def test_coroutines_manager_initialization(self, mock_wb_api, mock_wb_cabinet):
        """Test CoroutinesManager initialization with required attributes."""
        # Act
        manager = CoroutinesManager(mock_wb_api)

        # Assert
        assert manager._wb_api == mock_wb_api
        assert manager.shop_id == "test_shop_123"
        assert manager._session == mock_wb_api.session
        assert manager._wb_shop_data_manager is not None
        assert isinstance(manager._wb_shop_data_manager, WBShopDataManager)
        assert hasattr(manager, "_CoroutinesManager__keywords_for_advs")
        assert manager._adv_settings_dict is None
        assert manager._adv_settings_list is None


class TestCoroutinesManagerIntegrationScenarios:
    """Integration test scenarios for CoroutinesManager."""

    @pytest.mark.asyncio
    async def test_end_to_end_execution_flow(self, coroutines_manager):
        """Test complete end-to-end execution flow."""
        # Arrange
        adv1 = Mock(spec=AdvSetting)
        adv1.id = 1
        adv1.name = "Test Campaign 1"

        keyword1 = Mock(spec=CalculatedKeyword)
        keyword1.text = "test keyword 1"

        adv_settings = [adv1]
        keywords = [keyword1]

        # Mock dependencies
        with patch.object(
            coroutines_manager._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            with patch.object(coroutines_manager._wb_shop_data_manager, "get_calculated_keywords") as mock_get_keywords:
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    # Setup mocks
                    mock_get_active_advs.return_value = adv_settings
                    mock_get_keywords.return_value = asyncio.create_task(asyncio.sleep(0, result=keywords))

                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock()
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act
                    result = await coroutines_manager.update_cpm_bid_in_search_advs()

                    # Assert complete flow
                    assert result is None

                    # Verify call sequence
                    mock_get_active_advs.assert_called_once()
                    mock_get_keywords.assert_called_once_with(adv1)
                    mock_update_cpm_manager_class.assert_called_once_with("test_shop_123")
                    mock_update_cpm_manager.update_cpms_in_search_advs.assert_called_once()

                    # Verify data flow
                    call_args = mock_update_cpm_manager.update_cpms_in_search_advs.call_args[0][0]
                    assert len(call_args) == 1
                    assert call_args[0][0] == adv1
                    assert isinstance(call_args[0][1], asyncio.Task)
