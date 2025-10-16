"""Tests for TokenMonitoringIntegration."""

import pytest
from unittest.mock import MagicMock, patch

from app.modules.token_monitoring.integration import (
    TokenMonitoringIntegration,
    get_token_monitoring_integration,
    install_token_monitoring,
    uninstall_token_monitoring,
    is_token_monitoring_installed,
)


class TestTokenMonitoringIntegration:
    """Test cases for TokenMonitoringIntegration."""
    
    @pytest.fixture
    def integration(self):
        """Create integration instance."""
        return TokenMonitoringIntegration()
    
    def test_integration_initialization(self, integration):
        """Test integration initialization."""
        assert integration.monitoring_service is not None
        assert integration.is_installed == False
        assert integration._original_decorator is None
    
    def test_install_integration(self, integration):
        """Test installing token monitoring integration."""
        with patch('app.core.wb_api.http_request') as mock_http_module:
            mock_original_decorator = MagicMock()
            mock_http_module.try_except_decorator = mock_original_decorator
            
            # Mock the wrap method
            mock_enhanced_decorator = MagicMock()
            integration.monitoring_service.wrap_try_except_decorator = MagicMock(
                return_value=mock_enhanced_decorator
            )
            
            integration.install()
            
            # Verify installation
            assert integration.is_installed == True
            assert integration._original_decorator == mock_original_decorator
            assert mock_http_module.try_except_decorator == mock_enhanced_decorator
            
            integration.monitoring_service.wrap_try_except_decorator.assert_called_once_with(
                mock_original_decorator
            )
    
    def test_install_already_installed_warning(self, integration):
        """Test warning when installing already installed integration."""
        integration._is_installed = True
        
        with patch('app.modules.token_monitoring.integration.logger') as mock_logger:
            integration.install()
            
            mock_logger.warning.assert_called_once_with(
                "Token monitoring is already installed"
            )
    
    def test_install_error_handling(self, integration):
        """Test error handling during installation."""
        with patch('app.core.wb_api.http_request') as mock_http_module:
            mock_http_module.try_except_decorator = MagicMock()
            
            # Make wrap_try_except_decorator raise an exception
            integration.monitoring_service.wrap_try_except_decorator = MagicMock(
                side_effect=Exception("Wrap error")
            )
            
            with patch('app.modules.token_monitoring.integration.logger') as mock_logger:
                # The method should raise the exception after logging
                with pytest.raises(Exception, match="Wrap error"):
                    integration.install()
                
                # Verify that error was logged
                mock_logger.error.assert_called()
                error_call = mock_logger.error.call_args[0][0]
                assert "Failed to install token monitoring" in error_call
    
    def test_uninstall_integration(self, integration):
        """Test uninstalling token monitoring integration."""
        with patch('app.core.wb_api.http_request') as mock_http_module:
            mock_original_decorator = MagicMock()
            mock_enhanced_decorator = MagicMock()
            
            # Setup installed state
            integration._is_installed = True
            integration._original_decorator = mock_original_decorator
            mock_http_module.try_except_decorator = mock_enhanced_decorator
            
            integration.uninstall()
            
            # Verify uninstallation
            assert integration.is_installed == False
            assert integration._original_decorator is None
            assert mock_http_module.try_except_decorator == mock_original_decorator
    
    def test_uninstall_not_installed_warning(self, integration):
        """Test warning when uninstalling not installed integration."""
        assert integration.is_installed == False
        
        with patch('app.modules.token_monitoring.integration.logger') as mock_logger:
            integration.uninstall()
            
            mock_logger.warning.assert_called_once_with(
                "Token monitoring is not installed"
            )
    
    def test_uninstall_no_original_decorator_warning(self, integration):
        """Test warning when no original decorator found during uninstall."""
        with patch('app.core.wb_api.http_request'):
            # Setup installed state but no original decorator
            integration._is_installed = True
            integration._original_decorator = None
            
            with patch('app.modules.token_monitoring.integration.logger') as mock_logger:
                integration.uninstall()
                
                mock_logger.warning.assert_called_with(
                    "No original decorator found to restore"
                )
    
    def test_uninstall_error_handling(self, integration):
        """Test error handling during uninstallation."""
        integration._is_installed = True
        integration._original_decorator = MagicMock()
        
        with patch('app.core.wb_api.http_request') as mock_http_module:
            # Make setting try_except_decorator raise an exception
            def raise_on_set(value):
                raise Exception("Module error")
            
            type(mock_http_module).try_except_decorator = property(
                fget=lambda self: None,
                fset=lambda self, value: raise_on_set(value)
            )
            
            with patch('app.modules.token_monitoring.integration.logger') as mock_logger:
                # The method should raise the exception after logging
                with pytest.raises(Exception, match="Module error"):
                    integration.uninstall()
                
                # Verify that error was logged
                mock_logger.error.assert_called()
                error_call = mock_logger.error.call_args[0][0]
                assert "Failed to uninstall token monitoring" in error_call
    
    def test_is_installed_property(self, integration):
        """Test is_installed property."""
        assert integration.is_installed == False
        
        integration._is_installed = True
        assert integration.is_installed == True
        
        integration._is_installed = False
        assert integration.is_installed == False


class TestIntegrationGlobalFunctions:
    """Test global integration functions."""
    
    def test_get_token_monitoring_integration_singleton(self):
        """Test that get_token_monitoring_integration returns singleton."""
        integration1 = get_token_monitoring_integration()
        integration2 = get_token_monitoring_integration()
        
        assert integration1 is integration2
        assert isinstance(integration1, TokenMonitoringIntegration)
    
    def test_install_token_monitoring_global(self):
        """Test installing token monitoring globally."""
        with patch('app.modules.token_monitoring.integration.get_token_monitoring_integration') as mock_get:
            mock_integration = MagicMock()
            mock_get.return_value = mock_integration
            
            install_token_monitoring()
            
            mock_integration.install.assert_called_once()
    
    def test_uninstall_token_monitoring_global(self):
        """Test uninstalling token monitoring globally."""
        with patch('app.modules.token_monitoring.integration.get_token_monitoring_integration') as mock_get:
            mock_integration = MagicMock()
            mock_get.return_value = mock_integration
            
            uninstall_token_monitoring()
            
            mock_integration.uninstall.assert_called_once()
    
    def test_is_token_monitoring_installed_global(self):
        """Test checking if token monitoring is installed globally."""
        with patch('app.modules.token_monitoring.integration.get_token_monitoring_integration') as mock_get:
            mock_integration = MagicMock()
            mock_integration.is_installed = True
            mock_get.return_value = mock_integration
            
            result = is_token_monitoring_installed()
            
            assert result == True
    
    def test_is_token_monitoring_installed_false(self):
        """Test checking if token monitoring is installed when it's not."""
        with patch('app.modules.token_monitoring.integration.get_token_monitoring_integration') as mock_get:
            mock_integration = MagicMock()
            mock_integration.is_installed = False
            mock_get.return_value = mock_integration
            
            result = is_token_monitoring_installed()
            
            assert result == False


class TestTokenMonitoringServiceWrapping:
    """Test the actual wrapping functionality."""
    
    def test_service_wrapping_integration(self):
        """Test that the service properly wraps decorators."""
        integration = TokenMonitoringIntegration()
        
        # Mock original decorator with __name__ attribute
        original_decorator = MagicMock()
        original_decorator.__name__ = "test_decorator"
        
        # Mock the service's wrap method to return a test function
        def mock_wrap_method(original_decorator):
            def wrapped_decorator(*args, **kwargs):
                return f"wrapped_{original_decorator.__name__}"
            return wrapped_decorator
        
        with patch.object(integration.monitoring_service, 'wrap_try_except_decorator', mock_wrap_method):
            # Test wrapping
            result = integration.monitoring_service.wrap_try_except_decorator(original_decorator)
            
            # Verify the wrapper works
            assert callable(result)
            wrapped_result = result()
            assert wrapped_result == f"wrapped_{original_decorator.__name__}"