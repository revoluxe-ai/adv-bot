"""Integration module for installing token monitoring into the existing HTTP decorator."""

import logging
from typing import Any, Callable

from app.modules.token_monitoring.services.token_monitoring_service import TokenMonitoringService

logger = logging.getLogger(__name__)


class TokenMonitoringIntegration:
    """Integration class for installing token monitoring into the HTTP request system."""
    
    def __init__(self):
        self.monitoring_service = TokenMonitoringService()
        self._is_installed = False
        self._original_decorator = None
    
    def install(self) -> None:
        """
        Install token monitoring by wrapping the existing try_except_decorator.
        
        This method modifies the app.core.wb_api.http_request module to add
        token monitoring capabilities to all API calls.
        """
        if self._is_installed:
            logger.warning("Token monitoring is already installed")
            return
        
        try:
            # Import the http_request module
            import app.core.wb_api.http_request as http_request_module
            
            # Store reference to original decorator
            self._original_decorator = http_request_module.try_except_decorator
            
            # Create enhanced decorator
            enhanced_decorator = self.monitoring_service.wrap_try_except_decorator(
                self._original_decorator
            )
            
            # Replace the decorator in the module
            http_request_module.try_except_decorator = enhanced_decorator
            
            # Mark as installed
            self._is_installed = True
            
            logger.info("Token monitoring successfully installed in HTTP decorator")
            
        except Exception as e:
            logger.error(f"Failed to install token monitoring: {e}", exc_info=True)
            raise
    
    def uninstall(self) -> None:
        """
        Uninstall token monitoring by restoring the original try_except_decorator.
        """
        if not self._is_installed:
            logger.warning("Token monitoring is not installed")
            return
        
        try:
            import app.core.wb_api.http_request as http_request_module
            
            if self._original_decorator:
                # Restore original decorator
                http_request_module.try_except_decorator = self._original_decorator
                self._original_decorator = None
                self._is_installed = False
                
                logger.info("Token monitoring successfully uninstalled from HTTP decorator")
            else:
                logger.warning("No original decorator found to restore")
                
        except Exception as e:
            logger.error(f"Failed to uninstall token monitoring: {e}", exc_info=True)
            raise
    
    @property
    def is_installed(self) -> bool:
        """Check if token monitoring is currently installed."""
        return self._is_installed


# Global integration instance
_integration_instance = None


def get_token_monitoring_integration() -> TokenMonitoringIntegration:
    """Get or create the global token monitoring integration instance."""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = TokenMonitoringIntegration()
    return _integration_instance


def install_token_monitoring() -> None:
    """Install token monitoring globally."""
    integration = get_token_monitoring_integration()
    integration.install()


def uninstall_token_monitoring() -> None:
    """Uninstall token monitoring globally."""
    integration = get_token_monitoring_integration()
    integration.uninstall()


def is_token_monitoring_installed() -> bool:
    """Check if token monitoring is currently installed."""
    integration = get_token_monitoring_integration()
    return integration.is_installed