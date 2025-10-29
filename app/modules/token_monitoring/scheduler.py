"""Scheduler for token monitoring tasks."""

import asyncio
import logging
from datetime import datetime, time
from typing import Any, Dict, Optional

from app.modules.token_monitoring.services.token_expiration_service import (
    TokenExpirationService,
)
from app.modules.token_monitoring.services.notification_manager import (
    NotificationManager,
)

logger = logging.getLogger(__name__)


class TokenMonitoringScheduler:
    """Scheduler for running token monitoring tasks at regular intervals."""

    def __init__(
        self,
        expiration_service: TokenExpirationService | None = None,
        notification_manager: NotificationManager | None = None,
    ):
        """
        Initialize the scheduler.

        Args:
            expiration_service: Optional expiration service instance
            notification_manager: Optional notification manager instance
        """
        self.expiration_service = expiration_service or TokenExpirationService()
        self.notification_manager = notification_manager or NotificationManager()
        self._running = False
        self._task = None

    async def start_daily_expiration_check(self, check_time: time = time(9, 0)) -> None:
        """
        Start daily token expiration checking at specified time.

        Args:
            check_time: Time of day to run the check (default: 9:00 AM)
        """
        if self._running:
            logger.warning("Token monitoring scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._daily_check_loop(check_time))

        logger.info(f"Started daily token expiration check at {check_time}")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Token monitoring scheduler stopped")

    async def _daily_check_loop(self, check_time: time) -> None:
        """
        Main loop for daily expiration checks.

        Args:
            check_time: Time of day to run the check
        """
        while self._running:
            try:
                # Calculate seconds until next check time
                now = datetime.now()
                next_check = datetime.combine(now.date(), check_time)

                # If check time has passed today, schedule for tomorrow
                if next_check <= now:
                    next_check = datetime.combine(
                        now.date().replace(day=now.day + 1), check_time
                    )

                sleep_seconds = (next_check - now).total_seconds()

                logger.info(f"Next token expiration check scheduled for {next_check}")

                # Sleep until check time
                await asyncio.sleep(sleep_seconds)

                if self._running:
                    # Run the expiration check
                    await self._run_expiration_check()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in daily check loop: {e}", exc_info=True)
                # Sleep for 1 hour before retrying on error
                await asyncio.sleep(3600)

    async def _run_expiration_check(self) -> None:
        """Run the token expiration check."""
        try:
            logger.info("Starting scheduled token expiration check")

            stats = await self.expiration_service.check_token_expiration()

            logger.info(f"Completed token expiration check: {stats}")

            # Optional: Clean up old resolved notifications (weekly)
            if datetime.now().weekday() == 0:  # Monday
                try:
                    cleaned = (
                        await self.expiration_service.cleanup_resolved_notifications(30)
                    )
                    logger.info(f"Cleaned up {cleaned} old resolved notifications")
                except Exception as e:
                    logger.error(
                        f"Failed to clean up old notifications: {e}", exc_info=True
                    )

        except Exception as e:
            logger.error(f"Failed to run token expiration check: {e}", exc_info=True)

    async def run_manual_check(self) -> dict[str, Any]:
        """
        Run a manual token expiration check immediately.

        Returns:
            Dictionary with check statistics
        """
        logger.info("Running manual token expiration check")
        return await self.expiration_service.check_token_expiration()

    async def get_expiring_tokens_report(self, days_ahead: int = 30) -> dict[str, Any]:
        """
        Get a report of tokens expiring within specified days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            Dictionary with expiring tokens report
        """
        return await self.expiration_service.get_expiring_tokens_summary(days_ahead)

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        return self._running


# Global scheduler instance
_scheduler_instance = None


def get_token_monitoring_scheduler() -> TokenMonitoringScheduler:
    """Get or create the global token monitoring scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TokenMonitoringScheduler()
    return _scheduler_instance


async def start_token_monitoring_scheduler(check_time: time = time(9, 0)) -> None:
    """Start the global token monitoring scheduler."""
    scheduler = get_token_monitoring_scheduler()
    await scheduler.start_daily_expiration_check(check_time)


async def stop_token_monitoring_scheduler() -> None:
    """Stop the global token monitoring scheduler."""
    scheduler = get_token_monitoring_scheduler()
    await scheduler.stop()


async def run_manual_token_check() -> dict[str, Any]:
    """Run a manual token expiration check."""
    scheduler = get_token_monitoring_scheduler()
    return await scheduler.run_manual_check()


async def get_token_expiration_report(days_ahead: int = 30) -> dict[str, Any]:
    """Get a report of expiring tokens."""
    scheduler = get_token_monitoring_scheduler()
    return await scheduler.get_expiring_tokens_report(days_ahead)
