"""Startup module for initializing token monitoring system."""

import asyncio
import logging
from datetime import time
from typing import Optional

from app.modules.token_monitoring.integration import install_token_monitoring
from app.modules.token_monitoring.scheduler import start_token_monitoring_scheduler

logger = logging.getLogger(__name__)


async def initialize_token_monitoring(
    enable_decorator_monitoring: bool = True,
    enable_expiration_scheduler: bool = True,
    daily_check_time: time = time(9, 0)
) -> None:
    """
    Initialize the complete token monitoring system.
    
    Args:
        enable_decorator_monitoring: Whether to install HTTP decorator monitoring
        enable_expiration_scheduler: Whether to start the expiration scheduler
        daily_check_time: Time of day to run daily expiration checks
    """
    logger.info("Initializing token monitoring system...")
    
    try:
        # Install decorator monitoring for token deactivation detection
        if enable_decorator_monitoring:
            try:
                install_token_monitoring()
                logger.info("✓ Token deactivation monitoring installed")
            except Exception as e:
                logger.error(f"✗ Failed to install decorator monitoring: {e}")
                raise
        
        # Start expiration scheduler for proactive monitoring
        if enable_expiration_scheduler:
            try:
                await start_token_monitoring_scheduler(daily_check_time)
                logger.info(f"✓ Token expiration scheduler started (daily at {daily_check_time})")
            except Exception as e:
                logger.error(f"✗ Failed to start expiration scheduler: {e}")
                raise
        
        logger.info("Token monitoring system initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize token monitoring system: {e}")
        raise


async def shutdown_token_monitoring() -> None:
    """Shutdown the token monitoring system gracefully."""
    logger.info("Shutting down token monitoring system...")
    
    try:
        # Stop the scheduler
        from app.modules.token_monitoring.scheduler import stop_token_monitoring_scheduler
        await stop_token_monitoring_scheduler()
        logger.info("✓ Token expiration scheduler stopped")
        
        # Uninstall decorator monitoring
        from app.modules.token_monitoring.integration import uninstall_token_monitoring
        uninstall_token_monitoring()
        logger.info("✓ Token deactivation monitoring uninstalled")
        
        logger.info("Token monitoring system shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during token monitoring shutdown: {e}")


def setup_token_monitoring_for_app(
    enable_decorator_monitoring: bool = True,
    enable_expiration_scheduler: bool = True,
    daily_check_time: time = time(9, 0)
) -> None:
    """
    Setup token monitoring for application startup.
    
    This function can be called from your application's main startup routine.
    
    Args:
        enable_decorator_monitoring: Whether to install HTTP decorator monitoring
        enable_expiration_scheduler: Whether to start the expiration scheduler
        daily_check_time: Time of day to run daily expiration checks
    """
    try:
        # Create event loop if none exists
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Initialize token monitoring
        loop.run_until_complete(
            initialize_token_monitoring(
                enable_decorator_monitoring=enable_decorator_monitoring,
                enable_expiration_scheduler=enable_expiration_scheduler,
                daily_check_time=daily_check_time
            )
        )
        
    except Exception as e:
        logger.error(f"Failed to setup token monitoring: {e}")
        raise


# For backwards compatibility and convenience
def install_all_token_monitoring() -> None:
    """Install all token monitoring features with default settings."""
    setup_token_monitoring_for_app(
        enable_decorator_monitoring=True,
        enable_expiration_scheduler=True,
        daily_check_time=time(9, 0)  # 9:00 AM
    )