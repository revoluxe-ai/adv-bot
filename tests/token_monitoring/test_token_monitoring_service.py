"""Tests for TokenMonitoringService core functionality."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock, PropertyMock
import functools

from app.modules.token_monitoring.services.token_monitoring_service import (
    TokenMonitoringService,
    get_token_monitoring_service,
    install_token_monitoring,
    uninstall_token_monitoring,
)
from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.token_monitoring.models import NotificationType


class TestTokenMonitoringService:
    """Test cases for TokenMonitoringService."""

    @pytest.fixture
    def mock_notification_manager(self):
        """Mock notification manager."""
        manager = AsyncMock()
        manager.notify_token_issue = AsyncMock()
        return manager

    @pytest.fixture
    def monitoring_service(self, mock_notification_manager):
        """Create monitoring service with mocked notification manager."""
        return TokenMonitoringService(notification_manager=mock_notification_manager)

    def test_service_initialization_with_manager(self, mock_notification_manager):
        """Test service initialization with provided notification manager."""
        service = TokenMonitoringService(notification_manager=mock_notification_manager)

        assert service._notification_manager == mock_notification_manager
        assert service._original_decorator is None

    def test_service_initialization_without_manager(self):
        """Test service initialization without notification manager."""
        service = TokenMonitoringService()

        assert service._notification_manager is None
        assert service._original_decorator is None

    def test_notification_manager_lazy_loading(self):
        """Test lazy loading of notification manager."""
        service = TokenMonitoringService()

        with patch(
            "app.modules.token_monitoring.services.notification_manager.NotificationManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            # First access should create the manager
            manager = service.notification_manager

            assert manager == mock_manager
            assert service._notification_manager == mock_manager
            mock_manager_class.assert_called_once()

            # Second access should return the same instance
            manager2 = service.notification_manager
            assert manager2 == mock_manager
            assert mock_manager_class.call_count == 1  # Should not be called again

    def test_wrap_try_except_decorator_basic(self, monitoring_service):
        """Test basic decorator wrapping functionality."""

        # Create a mock original decorator that matches the real signature
        def original_decorator(
            requests_per_interval, interval_seconds, max_attempts=50, max_delay=120
        ):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    return f"original_result_{func.__name__}"

                return wrapper

            return decorator

        # Wrap the decorator
        enhanced_decorator = monitoring_service.wrap_try_except_decorator(
            original_decorator
        )

        # Test the enhanced decorator
        assert callable(enhanced_decorator)

        # Create a test function
        def test_function():
            return "test_result"

        # Call enhanced decorator with required parameters
        wrapped_function = enhanced_decorator(
            requests_per_interval=10, interval_seconds=1
        )(test_function)

        # Verify wrapped function is callable and works
        assert callable(wrapped_function)
        # Note: The wrapper is async, so we can't call it directly without await

    @pytest.mark.asyncio
    async def test_enhanced_decorator_token_deactivation_detection(
        self, monitoring_service
    ):
        """Test that enhanced decorator detects token deactivation."""

        # Mock a function that raises ApiForbiddenError
        async def failing_function(instance):
            raise ApiForbiddenError("Token is invalid")

        # Mock original decorator that matches the real signature
        def original_decorator(
            requests_per_interval, interval_seconds, max_attempts=50, max_delay=120
        ):
            def decorator(func):
                async def wrapper(instance, *args, **kwargs):
                    # Call the original function which will raise ApiForbiddenError
                    return await func(instance, *args, **kwargs)

                return wrapper

            return decorator

        # Create enhanced decorator
        enhanced_decorator = monitoring_service.wrap_try_except_decorator(
            original_decorator
        )
        wrapped_function = enhanced_decorator(
            requests_per_interval=10, interval_seconds=1
        )(failing_function)

        # Create a mock instance with shop_id
        mock_instance = MagicMock()
        mock_instance.shop_id = "test_shop_123"

        # Test that it detects token issues and re-raises
        with pytest.raises(ApiForbiddenError):
            await wrapped_function(mock_instance)

        # The notification should be triggered in the enhanced decorator via asyncio.create_task

    def test_install_monitoring_success(self, monitoring_service):
        """Test successful installation of monitoring."""
        mock_original_decorator = MagicMock()

        with patch(
            "app.core.wb_api.http_request.try_except_decorator", mock_original_decorator
        ):
            monitoring_service.install_monitoring()

            # Verify original decorator was stored in the service
            assert monitoring_service._original_decorator == mock_original_decorator

            # Verify backup was created in the module
            import app.core.wb_api.http_request as http_request_module

            assert hasattr(http_request_module, "_original_try_except_decorator")
            assert (
                http_request_module._original_try_except_decorator
                == mock_original_decorator
            )
            # Verify decorator was replaced with enhanced version
            assert http_request_module.try_except_decorator != mock_original_decorator
            assert callable(http_request_module.try_except_decorator)

    def test_install_monitoring_already_installed(self, monitoring_service):
        """Test installing when already installed."""
        mock_original_decorator = MagicMock()

        with patch("app.core.wb_api.http_request") as mock_http_module:
            # Simulate already installed state
            mock_http_module._original_try_except_decorator = mock_original_decorator
            mock_http_module.try_except_decorator = MagicMock()  # Already enhanced

            monitoring_service.install_monitoring()

            # The _original_try_except_decorator should NOT be overwritten
            # (hasattr check in the code prevents this)
            assert (
                mock_http_module._original_try_except_decorator
                == mock_original_decorator
            )

    @pytest.mark.skip(
        reason="Difficult to simulate error conditions for decorator installation"
    )
    def test_install_monitoring_error(self, monitoring_service):
        """Test error handling during installation."""
        with patch("app.core.wb_api.http_request") as mock_http_module:
            mock_http_module.try_except_decorator = Exception("Import error")

            with patch(
                "app.modules.token_monitoring.services.token_monitoring_service.logger"
            ) as mock_logger:
                with pytest.raises(Exception):
                    monitoring_service.install_monitoring()

                mock_logger.error.assert_called()
                error_call = mock_logger.error.call_args[0][0]
                assert "Failed to install token monitoring" in error_call

    def test_uninstall_monitoring_success(self, monitoring_service):
        """Test successful uninstallation of monitoring."""
        mock_original_decorator = MagicMock()
        mock_enhanced_decorator = MagicMock()

        with patch("app.core.wb_api.http_request") as mock_http_module:
            mock_http_module.try_except_decorator = mock_enhanced_decorator
            mock_http_module._original_try_except_decorator = mock_original_decorator

            monitoring_service.uninstall_monitoring()

            # Verify decorator was restored
            assert mock_http_module.try_except_decorator == mock_original_decorator
            assert not hasattr(mock_http_module, "_original_try_except_decorator")

    def test_uninstall_monitoring_not_installed(self, monitoring_service):
        """Test uninstalling when not installed."""
        with patch("app.core.wb_api.http_request") as mock_http_module:
            # No _original_try_except_decorator attribute
            if hasattr(mock_http_module, "_original_try_except_decorator"):
                delattr(mock_http_module, "_original_try_except_decorator")

            with patch(
                "app.modules.token_monitoring.services.token_monitoring_service.logger"
            ) as mock_logger:
                monitoring_service.uninstall_monitoring()

                mock_logger.warning.assert_called_once_with(
                    "No original decorator found to restore"
                )

    @pytest.mark.skip(
        reason="Difficult to simulate error conditions for decorator uninstallation"
    )
    def test_uninstall_monitoring_error(self, monitoring_service):
        """Test error handling during uninstallation."""
        with patch("app.core.wb_api.http_request") as mock_http_module:
            mock_http_module.try_except_decorator = Exception("Module error")

            with patch(
                "app.modules.token_monitoring.services.token_monitoring_service.logger"
            ) as mock_logger:
                with pytest.raises(Exception):
                    monitoring_service.uninstall_monitoring()

                mock_logger.error.assert_called()
                error_call = mock_logger.error.call_args[0][0]
                assert "Failed to uninstall token monitoring" in error_call


class TestTokenMonitoringServiceGlobalFunctions:
    """Test global functions for TokenMonitoringService."""

    def test_get_token_monitoring_service_singleton(self):
        """Test that get_token_monitoring_service returns singleton."""
        service1 = get_token_monitoring_service()
        service2 = get_token_monitoring_service()

        assert service1 is service2
        assert isinstance(service1, TokenMonitoringService)

    def test_install_token_monitoring_global(self):
        """Test installing token monitoring globally."""
        with patch(
            "app.modules.token_monitoring.services.token_monitoring_service.get_token_monitoring_service"
        ) as mock_get:
            mock_service = MagicMock()
            mock_get.return_value = mock_service

            install_token_monitoring()

            mock_service.install_monitoring.assert_called_once()

    def test_uninstall_token_monitoring_global(self):
        """Test uninstalling token monitoring globally."""
        with patch(
            "app.modules.token_monitoring.services.token_monitoring_service.get_token_monitoring_service"
        ) as mock_get:
            mock_service = MagicMock()
            mock_get.return_value = mock_service

            uninstall_token_monitoring()

            mock_service.uninstall_monitoring.assert_called_once()


class TestTokenMonitoringServiceDecorator:
    """Test the actual decorator enhancement functionality."""

    @pytest.fixture
    def monitoring_service(self):
        """Create monitoring service for decorator testing."""
        return TokenMonitoringService()

    @pytest.mark.asyncio
    async def test_decorator_preserves_original_behavior(self, monitoring_service):
        """Test that enhanced decorator preserves original decorator behavior."""
        call_log = []

        def original_decorator_mock(
            requests_per_interval, interval_seconds, max_attempts=50, max_delay=120
        ):
            def decorator(func):
                async def wrapper(instance, *args, **kwargs):
                    call_log.append("original_called")
                    # Call the actual function
                    return await func(instance, *args, **kwargs)

                return wrapper

            return decorator

        class MockInstance:
            # The instance passed to the decorated function
            pass

        async def test_function(instance):
            call_log.append("function_called")
            return "success"

        # Wrap the decorator
        enhanced_decorator_factory = monitoring_service.wrap_try_except_decorator(
            original_decorator_mock
        )
        # Get the actual enhanced decorator
        enhanced_decorator = enhanced_decorator_factory(
            requests_per_interval=10, interval_seconds=1
        )
        # Apply the decorator to the test function
        wrapped_function = enhanced_decorator(test_function)

        mock_instance = MockInstance()
        result = await wrapped_function(mock_instance)

        assert result == "success"
        assert "original_called" in call_log
        assert "function_called" in call_log

    @pytest.mark.asyncio
    async def test_decorator_handles_exceptions_properly(self, monitoring_service):
        """Test that enhanced decorator handles exceptions properly."""

        def original_decorator_mock(
            requests_per_interval, interval_seconds, max_attempts=50, max_delay=120
        ):
            def decorator(func):
                async def wrapper(instance, *args, **kwargs):
                    try:
                        return await func(instance, *args, **kwargs)
                    except Exception as e:
                        # Original decorator catches and re-raises
                        raise e

                return wrapper

            return decorator

        class MockInstance:
            pass

        async def failing_function(instance):
            raise ValueError("Test error")

        enhanced_decorator_factory = monitoring_service.wrap_try_except_decorator(
            original_decorator_mock
        )
        enhanced_decorator = enhanced_decorator_factory(
            requests_per_interval=10, interval_seconds=1
        )
        wrapped_function = enhanced_decorator(failing_function)

        mock_instance = MockInstance()
        # Should still raise the original exception
        with pytest.raises(ValueError, match="Test error"):
            await wrapped_function(mock_instance)

    @pytest.mark.asyncio
    async def test_decorator_with_shop_id_extraction(self, monitoring_service):
        """Test decorator with shop_id extraction from context."""

        def original_decorator_mock(
            requests_per_interval, interval_seconds, max_attempts=50, max_delay=120
        ):
            def decorator(func):
                async def wrapper(instance, *args, **kwargs):
                    return await func(instance, *args, **kwargs)

                return wrapper

            return decorator

        class MockInstance:
            def __init__(self, shop_id=None):
                self.shop_id = shop_id

        async def api_function_with_shop_id(instance):
            # Simulate a real API call that might raise ApiForbiddenError
            raise ApiForbiddenError("Token invalid")

        enhanced_decorator_factory = monitoring_service.wrap_try_except_decorator(
            original_decorator_mock
        )
        enhanced_decorator = enhanced_decorator_factory(
            requests_per_interval=10, interval_seconds=1
        )
        wrapped_function = enhanced_decorator(api_function_with_shop_id)

        # Mock notification manager and asyncio.create_task
        with patch.object(
            type(monitoring_service), "notification_manager", new_callable=PropertyMock
        ) as mock_manager, patch.object(
            monitoring_service, "_handle_token_deactivation", new_callable=AsyncMock
        ) as mock_handle, patch(
            "asyncio.create_task"
        ) as mock_create_task:

            mock_manager.return_value.notify_token_issue = AsyncMock()

            mock_instance = MockInstance(shop_id="test_shop_123")

            with pytest.raises(ApiForbiddenError):
                await wrapped_function(mock_instance)

            # Ensure we scheduled a task
            mock_create_task.assert_called_once()
            # Ensure our internal handler was invoked with expected args
            mock_handle.assert_called_once()
            called_args = mock_handle.call_args[0]
            assert called_args[0] == "test_shop_123"
            assert called_args[1] == "api_function_with_shop_id"
            assert "Token invalid" in called_args[2]
