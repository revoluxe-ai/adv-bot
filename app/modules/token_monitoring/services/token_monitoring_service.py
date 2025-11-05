"""Token monitoring service for detecting and handling token deactivation events."""

import asyncio
import logging
from typing import Any
from collections.abc import Callable

from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.token_monitoring.models import NotificationType

logger = logging.getLogger(__name__)


class TokenMonitoringService:
    """Service for monitoring token deactivation events during API calls."""

    def __init__(self, notification_manager=None):
        """
        Initialize the token monitoring service.

        Args:
            notification_manager: Optional notification manager instance.
                                 If None, will be imported lazily to avoid circular imports.
        """
        self._notification_manager = notification_manager
        self._original_decorator = None

    @property
    def notification_manager(self):
        """Lazy-load notification manager to avoid circular imports."""
        if self._notification_manager is None:
            from app.modules.token_monitoring.services.notification_manager import (
                NotificationManager,
            )

            self._notification_manager = NotificationManager()
        return self._notification_manager

    def wrap_try_except_decorator(self, original_decorator: Callable) -> Callable:
        """
        Wrap the existing try_except_decorator to add token monitoring capabilities.

        This method preserves the original decorator functionality while adding
        token deactivation detection and notification capabilities.

        Args:
            original_decorator: The original try_except_decorator function

        Returns:
            Enhanced decorator with token monitoring
        """
        self._original_decorator = original_decorator

        def enhanced_try_except_decorator(
            requests_per_interval: int,
            interval_seconds: int | float,
            max_attempts: int = 50,
            max_delay: int = 120,
        ) -> Callable:
            """Enhanced decorator that monitors for token deactivation."""

            def decorator(func: Callable) -> Callable:
                # First apply the original decorator
                original_decorated_func = original_decorator(
                    requests_per_interval, interval_seconds, max_attempts, max_delay
                )(func)

                async def monitoring_wrapper(
                    instance: Any, *args: Any, **kwargs: Any
                ) -> Any:
                    """Wrapper that adds token monitoring around the original decorated function."""
                    try:
                        # Call the original decorated function
                        result = await original_decorated_func(
                            instance, *args, **kwargs
                        )
                        return result

                    except ApiForbiddenError as e:
                        # Token deactivation detected - all tokens have failed
                        shop_id = getattr(instance, "shop_id", None)

                        if shop_id:
                            logger.warning(
                                f"Token deactivation detected for shop {shop_id} "
                                f"during {func.__name__} call: {e}"
                            )

                            # Send notification asynchronously (don't block the main flow)
                            asyncio.create_task(
                                self._handle_token_deactivation(
                                    shop_id, func.__name__, str(e)
                                )
                            )
                        else:
                            logger.warning(
                                f"Token deactivation detected but no shop_id available "
                                f"during {func.__name__} call: {e}"
                            )

                        # Re-raise the exception to maintain existing behavior
                        raise

                return monitoring_wrapper

            return decorator

        return enhanced_try_except_decorator

    async def _handle_token_deactivation(
        self, shop_id: str, method_name: str, error_details: str
    ) -> None:
        """
        Handle token deactivation event by sending notifications.

        Args:
            shop_id: The shop ID where token deactivation occurred
            method_name: The API method that failed
            error_details: Details about the error
        """
        try:
            logger.info(f"Handling token deactivation for shop {shop_id}")

            # Send deactivation notification
            await self.notification_manager.notify_token_issue(
                shop_id=shop_id,
                notification_type=NotificationType.TOKEN_DEACTIVATED.value,
                context={
                    "method_name": method_name,
                    "error_details": error_details,
                },
            )

            logger.info(f"Token deactivation notification sent for shop {shop_id}")

        except Exception as notification_error:
            # Log notification errors but don't propagate them
            logger.error(
                f"Failed to send token deactivation notification for shop {shop_id}: "
                f"{notification_error}",
                exc_info=True,
            )

    def install_monitoring(self) -> None:
        """
        Install token monitoring by replacing the original try_except_decorator.

        This method should be called during application startup to enable
        token monitoring across all API calls.
        """
        try:
            # Import the original decorator
            from app.core.wb_api.http_request import try_except_decorator

            # Create enhanced version
            enhanced_decorator = self.wrap_try_except_decorator(try_except_decorator)

            # Replace the original decorator in the module
            import app.core.wb_api.http_request as http_request_module

            # Store reference to original for potential rollback
            if not hasattr(http_request_module, "_original_try_except_decorator"):
                http_request_module._original_try_except_decorator = ( # type: ignore[attr-defined]
                    try_except_decorator
                )

            # Replace with enhanced version
            http_request_module.try_except_decorator = enhanced_decorator

            logger.info("Token monitoring successfully installed")

        except Exception as e:
            logger.error(f"Failed to install token monitoring: {e}", exc_info=True)
            raise

    def uninstall_monitoring(self) -> None:
        """
        Uninstall token monitoring by restoring the original try_except_decorator.

        This method can be used for testing or if monitoring needs to be disabled.
        """
        try:
            import app.core.wb_api.http_request as http_request_module

            if hasattr(http_request_module, "_original_try_except_decorator"):
                # Restore original decorator
                http_request_module.try_except_decorator = (
                    http_request_module._original_try_except_decorator
                )
                delattr(http_request_module, "_original_try_except_decorator")

                logger.info("Token monitoring successfully uninstalled")
            else:
                logger.warning("No original decorator found to restore")

        except Exception as e:
            logger.error(f"Failed to uninstall token monitoring: {e}", exc_info=True)
            raise


# Global instance for convenience
_monitoring_service = None


def get_token_monitoring_service() -> TokenMonitoringService:
    """Get or create the global token monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = TokenMonitoringService()
    return _monitoring_service


def install_token_monitoring() -> None:
    """Install token monitoring globally."""
    service = get_token_monitoring_service()
    service.install_monitoring()


def uninstall_token_monitoring() -> None:
    """Uninstall token monitoring globally."""
    service = get_token_monitoring_service()
    service.uninstall_monitoring()
