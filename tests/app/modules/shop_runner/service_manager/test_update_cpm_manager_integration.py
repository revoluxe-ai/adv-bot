"""
Integration tests for UpdateCPMManager and its interaction with CoroutinesManager.

These tests focus on the integration between CoroutinesManager.update_cpm_bid_in_search_advs
and the UpdateCPMManager service, verifying correct data flow and error handling.
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


@pytest.fixture
def mock_wb_cabinet():
    """Mock WBCabinet for testing."""
    cabinet = Mock()
    cabinet.shop_id = "integration_shop_456"
    cabinet.id = 1
    return cabinet


@pytest.fixture
def mock_wb_api(mock_wb_cabinet):
    """Mock WBApi for testing."""
    api = Mock()
    api.wb_cabinet = mock_wb_cabinet
    api.shop_id = "integration_shop_456"
    api.session = AsyncMock()
    return api


@pytest.fixture
def sample_adv_setting():
    """Sample AdvSetting with realistic data."""
    adv = Mock()
    adv.id = 100
    adv.adv_id = 12345
    adv.search_adv_id = 54321
    adv.name = "Integration Test Campaign"
    adv.max_cpm = 75
    adv.max_place = 3
    adv.nmids = [111222, 333444]
    adv.bot_active = True
    adv.bidder_step = 5
    return adv


@pytest.fixture
def sample_calculated_keywords():
    """Sample calculated keywords for testing."""
    keyword1 = Mock()
    keyword1.text = "integration keyword 1"
    keyword1.keyword_setting_original_id = "100"
    keyword1.rating_by_predict_ctr = 0.8
    keyword1.predict_ctr = 0.15

    keyword2 = Mock()
    keyword2.text = "integration keyword 2"
    keyword2.keyword_setting_original_id = "101"
    keyword2.rating_by_predict_ctr = 0.6
    keyword2.predict_ctr = 0.12

    return [keyword1, keyword2]


@pytest.fixture
def coroutines_manager_integration(mock_wb_api):
    """CoroutinesManager instance for integration testing."""
    return CoroutinesManager(mock_wb_api)


class TestUpdateCPMManagerIntegration:
    """Integration tests for UpdateCPMManager with CoroutinesManager."""

    @pytest.mark.asyncio
    async def test_successful_integration_flow(
        self, coroutines_manager_integration, sample_adv_setting, sample_calculated_keywords
    ):
        """Test successful integration between CoroutinesManager and UpdateCPMManager."""
        # Arrange
        adv_settings = [sample_adv_setting]

        with patch.object(
            coroutines_manager_integration._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager_integration._wb_shop_data_manager,
                "get_calculated_keywords",
                return_value=asyncio.create_task(asyncio.sleep(0, result=sample_calculated_keywords)),
            ) as mock_get_keywords:
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock()
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act
                    result = await coroutines_manager_integration.update_cpm_bid_in_search_advs()

                    # Assert integration points
                    assert result is None

                    # Verify CoroutinesManager called data manager correctly
                    mock_get_active_advs.assert_called_once()
                    mock_get_keywords.assert_called_once_with(sample_adv_setting)

                    # Verify UpdateCPMManager was created with correct shop_id
                    mock_update_cpm_manager_class.assert_called_once_with("integration_shop_456")

                    # Verify UpdateCPMManager received correct data structure
                    mock_update_cpm_manager.update_cpms_in_search_advs.assert_called_once()
                    call_args = mock_update_cpm_manager.update_cpms_in_search_advs.call_args[0][0]

                    # Validate adv_keywords_coro structure
                    assert isinstance(call_args, list)
                    assert len(call_args) == 1

                    adv, keywords_coro = call_args[0]
                    assert adv == sample_adv_setting
                    assert isinstance(keywords_coro, asyncio.Task)

                    # Verify keywords can be resolved
                    resolved_keywords = await keywords_coro
                    assert resolved_keywords == sample_calculated_keywords

    @pytest.mark.asyncio
    async def test_integration_with_multiple_advs_and_keywords(self, coroutines_manager_integration):
        """Test integration with multiple advertisements and keywords."""
        # Arrange
        adv1 = Mock()
        adv1.id = 1
        adv1.name = "Campaign 1"
        adv1.search_adv_id = 101
        adv1.max_cpm = 50

        adv2 = Mock()
        adv2.id = 2
        adv2.name = "Campaign 2"
        adv2.search_adv_id = 102
        adv2.max_cpm = 60

        adv_settings = [adv1, adv2]

        keywords1 = [Mock(text="keyword1")]
        keywords2 = [Mock(text="keyword2")]

        async def mock_get_keywords_side_effect(adv):
            if adv == adv1:
                return keywords1
            elif adv == adv2:
                return keywords2
            return []

        with patch.object(
            coroutines_manager_integration._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager_integration._wb_shop_data_manager,
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
                    await coroutines_manager_integration.update_cpm_bid_in_search_advs()

                    # Assert
                    call_args = mock_update_cpm_manager.update_cpms_in_search_advs.call_args[0][0]
                    assert len(call_args) == 2

                    # Verify first advertisement and keywords
                    adv_1, keywords_coro_1 = call_args[0]
                    assert adv_1 == adv1
                    resolved_keywords_1 = await keywords_coro_1
                    assert resolved_keywords_1 == keywords1

                    # Verify second advertisement and keywords
                    adv_2, keywords_coro_2 = call_args[1]
                    assert adv_2 == adv2
                    resolved_keywords_2 = await keywords_coro_2
                    assert resolved_keywords_2 == keywords2

    @pytest.mark.asyncio
    async def test_integration_error_propagation_from_data_manager(self, coroutines_manager_integration):
        """Test that errors from WBShopDataManager propagate correctly."""
        # Arrange
        with patch.object(
            coroutines_manager_integration._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.side_effect = Exception("Data manager error")

            # Act & Assert
            with pytest.raises(Exception, match="Data manager error"):
                await coroutines_manager_integration.update_cpm_bid_in_search_advs()

    @pytest.mark.asyncio
    async def test_integration_error_propagation_from_update_cpm_manager(
        self, coroutines_manager_integration, sample_adv_setting, sample_calculated_keywords
    ):
        """Test that errors from UpdateCPMManager propagate correctly."""
        # Arrange
        adv_settings = [sample_adv_setting]

        with patch.object(
            coroutines_manager_integration._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager_integration._wb_shop_data_manager,
                "get_calculated_keywords",
                return_value=asyncio.create_task(asyncio.sleep(0, result=sample_calculated_keywords)),
            ):
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock(
                        side_effect=Exception("UpdateCPMManager error")
                    )
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act & Assert
                    with pytest.raises(Exception, match="UpdateCPMManager error"):
                        await coroutines_manager_integration.update_cpm_bid_in_search_advs()

    @pytest.mark.asyncio
    async def test_integration_with_empty_keywords(self, coroutines_manager_integration, sample_adv_setting):
        """Test integration when keywords list is empty."""
        # Arrange
        adv_settings = [sample_adv_setting]
        empty_keywords = []

        with patch.object(
            coroutines_manager_integration._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager_integration._wb_shop_data_manager,
                "get_calculated_keywords",
                return_value=asyncio.create_task(asyncio.sleep(0, result=empty_keywords)),
            ) as mock_get_keywords:
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock()
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act
                    result = await coroutines_manager_integration.update_cpm_bid_in_search_advs()

                    # Assert
                    assert result is None
                    mock_update_cpm_manager.update_cpms_in_search_advs.assert_called_once()

                    call_args = mock_update_cpm_manager.update_cpms_in_search_advs.call_args[0][0]
                    adv, keywords_coro = call_args[0]
                    assert adv == sample_adv_setting

                    resolved_keywords = await keywords_coro
                    assert resolved_keywords == empty_keywords

    @pytest.mark.asyncio
    async def test_integration_task_creation_and_resolution(
        self, coroutines_manager_integration, sample_adv_setting, sample_calculated_keywords
    ):
        """Test that asyncio.Tasks are properly created and can be resolved."""
        # Arrange
        adv_settings = [sample_adv_setting]

        with patch.object(
            coroutines_manager_integration._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            call_count = 0

            async def mock_get_keywords(adv):
                nonlocal call_count
                call_count += 1
                # Simulate some async work
                await asyncio.sleep(0.01)
                return sample_calculated_keywords

            with patch.object(
                coroutines_manager_integration._wb_shop_data_manager,
                "get_calculated_keywords",
                side_effect=lambda adv: asyncio.create_task(mock_get_keywords(adv)),
            ) as mock_get_keywords_patch:
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()

                    async def verify_task_resolution(adv_keywords_coro):
                        # Verify task can be resolved
                        assert len(adv_keywords_coro) == 1
                        adv, keywords_task = adv_keywords_coro[0]

                        # Task should be a proper asyncio.Task
                        assert isinstance(keywords_task, asyncio.Task)
                        assert not keywords_task.done()

                        # Resolve the task
                        resolved_keywords = await keywords_task
                        assert resolved_keywords == sample_calculated_keywords
                        assert keywords_task.done()

                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock(side_effect=verify_task_resolution)
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act
                    await coroutines_manager_integration.update_cpm_bid_in_search_advs()

                    # Assert
                    assert call_count == 1
                    mock_update_cpm_manager.update_cpms_in_search_advs.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_shop_id_consistency(
        self, coroutines_manager_integration, sample_adv_setting, sample_calculated_keywords
    ):
        """Test that shop_id is consistently used throughout the integration."""
        # Arrange
        adv_settings = [sample_adv_setting]

        with patch.object(
            coroutines_manager_integration._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager_integration._wb_shop_data_manager,
                "get_calculated_keywords",
                return_value=asyncio.create_task(asyncio.sleep(0, result=sample_calculated_keywords)),
            ):
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock()
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act
                    await coroutines_manager_integration.update_cpm_bid_in_search_advs()

                    # Assert shop_id consistency
                    expected_shop_id = "integration_shop_456"

                    # Verify CoroutinesManager has correct shop_id
                    assert coroutines_manager_integration.shop_id == expected_shop_id

                    # Verify WBShopDataManager has correct shop_id
                    assert coroutines_manager_integration._wb_shop_data_manager.shop_id == expected_shop_id

                    # Verify UpdateCPMManager was created with correct shop_id
                    mock_update_cpm_manager_class.assert_called_once_with(expected_shop_id)


class TestCoroutinesManagerUpdateCPMManagerPerformance:
    """Performance and stress tests for the integration."""

    @pytest.mark.asyncio
    async def test_integration_with_large_number_of_advs(self, coroutines_manager_integration):
        """Test integration performance with many advertisements."""
        # Arrange
        num_advs = 50
        adv_settings = []
        for i in range(num_advs):
            adv = Mock()
            adv.id = i
            adv.name = f"Campaign {i}"
            adv_settings.append(adv)

        mock_keywords = [Mock(text=f"keyword{i}") for i in range(3)]

        with patch.object(
            coroutines_manager_integration._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager_integration._wb_shop_data_manager,
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
                    start_time = asyncio.get_event_loop().time()
                    await coroutines_manager_integration.update_cpm_bid_in_search_advs()
                    end_time = asyncio.get_event_loop().time()

                    # Assert
                    execution_time = end_time - start_time
                    assert execution_time < 1.0  # Should complete within 1 second

                    # Verify all advs were processed
                    call_args = mock_update_cpm_manager.update_cpms_in_search_advs.call_args[0][0]
                    assert len(call_args) == num_advs
                    assert mock_get_keywords.call_count == num_advs

    @pytest.mark.asyncio
    async def test_integration_concurrent_task_handling(self, coroutines_manager_integration):
        """Test that concurrent tasks are handled correctly."""
        # Arrange
        adv1 = Mock(id=1, name="Concurrent Campaign 1")
        adv2 = Mock(id=2, name="Concurrent Campaign 2")
        adv_settings = [adv1, adv2]

        keywords1 = [Mock(text="concurrent keyword 1")]
        keywords2 = [Mock(text="concurrent keyword 2")]

        call_order = []

        async def mock_get_keywords_with_delay(adv):
            call_order.append(f"start_{adv.id}")
            # Simulate different processing times
            if adv.id == 1:
                await asyncio.sleep(0.02)
            else:
                await asyncio.sleep(0.01)
            call_order.append(f"end_{adv.id}")
            return keywords1 if adv.id == 1 else keywords2

        with patch.object(
            coroutines_manager_integration._wb_shop_data_manager, "get_active_advs", new_callable=AsyncMock
        ) as mock_get_active_advs:
            mock_get_active_advs.return_value = adv_settings

            with patch.object(
                coroutines_manager_integration._wb_shop_data_manager,
                "get_calculated_keywords",
                side_effect=lambda adv: asyncio.create_task(mock_get_keywords_with_delay(adv)),
            ):
                with patch(
                    "app.modules.shop_runner.service_manager.services.update_cpm.UpdateCPMManager"
                ) as mock_update_cpm_manager_class:
                    mock_update_cpm_manager = Mock()
                    mock_update_cpm_manager.update_cpms_in_search_advs = AsyncMock()
                    mock_update_cpm_manager_class.return_value = mock_update_cpm_manager

                    # Act
                    await coroutines_manager_integration.update_cpm_bid_in_search_advs()

                    # Assert
                    # Tasks should be created concurrently (starts interleaved)
                    assert "start_1" in call_order
                    assert "start_2" in call_order
                    assert call_order.index("start_2") < call_order.index("end_1")  # Task 2 starts before Task 1 ends

                    # But both should complete
                    assert "end_1" in call_order
                    assert "end_2" in call_order
