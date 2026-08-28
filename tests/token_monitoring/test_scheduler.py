"""Tests for TokenMonitoringScheduler."""

import asyncio
import datetime
import pytest
from datetime import time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.token_monitoring.scheduler import (
    TokenMonitoringScheduler,
    get_token_monitoring_scheduler,
    start_token_monitoring_scheduler,
    stop_token_monitoring_scheduler,
    run_manual_token_check,
    get_token_expiration_report,
)


class TestTokenMonitoringScheduler:
    """Test cases for TokenMonitoringScheduler."""

    @pytest.fixture
    def mock_expiration_service(self):
        """Mock token expiration service."""
        service = AsyncMock(return_value=None)
        service.check_token_expiration = AsyncMock(
            return_value={
                "total_tokens_checked": 10,
                "expiring_tokens_found": 3,
                "notifications_sent": 2,
            }
        )
        service.cleanup_resolved_notifications = AsyncMock(return_value=5)
        service.get_expiring_tokens_summary = AsyncMock(
            return_value={"tokens_expiring_soon": 2, "total_warnings": 5}
        )
        return service

    @pytest.fixture
    def mock_notification_manager(self):
        """Mock notification manager."""
        return AsyncMock(return_value=None)

    @pytest.fixture
    def scheduler(self, mock_expiration_service, mock_notification_manager):
        """Create scheduler instance with mocked services."""
        return TokenMonitoringScheduler(
            expiration_service=mock_expiration_service,
            notification_manager=mock_notification_manager,
        )

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler.expiration_service is not None
        assert scheduler.notification_manager is not None
        assert not scheduler.is_running
        assert scheduler._task is None

    @pytest.mark.asyncio
    async def test_start_daily_expiration_check(self, scheduler):
        """Test starting daily expiration check."""
        check_time = time(10, 30)

        with patch("asyncio.create_task") as mock_create_task:
            mock_task = AsyncMock(return_value=None)
            mock_create_task.return_value = mock_task

            await scheduler.start_daily_expiration_check(check_time)

            assert scheduler.is_running
            assert scheduler._task == mock_task
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_already_running_warning(self, scheduler):
        """Test warning when starting scheduler that's already running."""
        scheduler._running = True

        with patch("app.modules.token_monitoring.scheduler.logger") as mock_logger:
            await scheduler.start_daily_expiration_check()

            mock_logger.warning.assert_called_once_with(
                "Token monitoring scheduler is already running"
            )

    @pytest.mark.asyncio
    async def test_stop_scheduler(self, scheduler):
        """Test stopping the scheduler."""

        # Setup running scheduler with a real task
        async def dummy_coro():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                pass

        mock_task = asyncio.create_task(dummy_coro())

        scheduler._running = True
        scheduler._task = mock_task

        await scheduler.stop()

        assert not scheduler.is_running
        assert scheduler._task is None
        assert mock_task.cancelled()

    @pytest.mark.asyncio
    async def test_stop_not_running(self, scheduler):
        """Test stopping scheduler when not running."""
        assert not scheduler.is_running

        await scheduler.stop()  # Should not raise error

        assert not scheduler.is_running

    @pytest.mark.asyncio
    async def test_daily_check_loop_timing_calculation(self, scheduler):
        """Test daily check loop timing calculation."""
        check_time = time(9, 0)

        # Mock current time to be 8:00 AM
        mock_now = datetime.datetime(2025, 9, 28, 8, 0, 0)

        with patch("app.modules.token_monitoring.scheduler.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.datetime.combine

            with patch(
                "app.modules.token_monitoring.scheduler.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep:
                # Make the first sleep raise CancelledError to exit loop
                mock_sleep.side_effect = asyncio.CancelledError()

                scheduler._running = True

                try:
                    await scheduler._daily_check_loop(check_time)
                except asyncio.CancelledError:
                    pass  # Expected

                # Should sleep for 1 hour (until 9:00 AM)
                expected_sleep = 3600  # 1 hour in seconds
                actual_sleep = mock_sleep.call_args[0][0]
                assert abs(actual_sleep - expected_sleep) < 60  # Within 1 minute

    @pytest.mark.asyncio
    async def test_daily_check_loop_next_day_scheduling(self, scheduler):
        """Test scheduling for next day when current time is after check time."""
        check_time = time(9, 0)

        # Mock current time to be 10:00 AM (after check time)
        mock_now = datetime.datetime(2025, 9, 28, 10, 0, 0)

        with patch("app.modules.token_monitoring.scheduler.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.datetime.combine

            with patch(
                "app.modules.token_monitoring.scheduler.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()

                scheduler._running = True

                try:
                    await scheduler._daily_check_loop(check_time)
                except asyncio.CancelledError:
                    pass  # Expected

                # Should sleep for 23 hours (until 9:00 AM tomorrow)
                expected_sleep = 23 * 3600  # 23 hours in seconds
                actual_sleep = mock_sleep.call_args[0][0]
                assert abs(actual_sleep - expected_sleep) < 60  # Within 1 minute

    @pytest.mark.asyncio
    async def test_daily_check_loop_error_handling(self, scheduler):
        """Test error handling in daily check loop."""
        check_time = time(9, 0)

        with patch("app.modules.token_monitoring.scheduler.datetime") as mock_datetime:
            mock_datetime.now.side_effect = Exception("Time calculation error")

            with patch("asyncio.sleep") as mock_sleep:
                # First sleep for error recovery, second to exit
                mock_sleep.side_effect = [None, asyncio.CancelledError()]

                with patch(
                    "app.modules.token_monitoring.scheduler.logger"
                ) as mock_logger:
                    scheduler._running = True

                    with pytest.raises(asyncio.CancelledError):
                        await scheduler._daily_check_loop(check_time)

                    # Should log error and sleep for 1 hour
                    mock_logger.error.assert_called()
                    assert mock_sleep.call_args_list[0][0][0] == 3600  # 1 hour

    @pytest.mark.asyncio
    async def test_run_expiration_check_success(
        self, scheduler, mock_expiration_service
    ):
        """Test successful expiration check execution."""
        expected_stats = {
            "total_tokens_checked": 10,
            "expiring_tokens_found": 3,
            "notifications_sent": 2,
        }
        mock_expiration_service.check_token_expiration.return_value = expected_stats

        with patch("app.modules.token_monitoring.scheduler.logger") as mock_logger:
            await scheduler._run_expiration_check()

            mock_expiration_service.check_token_expiration.assert_called_once()
            mock_logger.info.assert_called()
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any(
                "Starting scheduled token expiration check" in call
                for call in log_calls
            )
            assert any("Completed token expiration check" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_run_expiration_check_with_cleanup(
        self, scheduler, mock_expiration_service
    ):
        """Test expiration check with Monday cleanup."""
        with patch("app.modules.token_monitoring.scheduler.datetime") as mock_datetime:
            # Mock Monday (weekday = 0)
            mock_now = MagicMock()
            mock_now.weekday.return_value = 0
            mock_datetime.now.return_value = mock_now

            mock_expiration_service.cleanup_resolved_notifications.return_value = 5

            with patch("app.modules.token_monitoring.scheduler.logger") as mock_logger:
                await scheduler._run_expiration_check()

                # Should run cleanup on Monday
                mock_expiration_service.cleanup_resolved_notifications.assert_called_once_with(
                    30
                )
                mock_logger.info.assert_called()
                log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any(
                    "Cleaned up 5 old resolved notifications" in call
                    for call in log_calls
                )

    @pytest.mark.asyncio
    async def test_run_expiration_check_cleanup_error(
        self, scheduler, mock_expiration_service
    ):
        """Test expiration check with cleanup error."""
        with patch("app.modules.token_monitoring.scheduler.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 0  # Monday
            mock_datetime.now.return_value = mock_now

            mock_expiration_service.cleanup_resolved_notifications.side_effect = (
                Exception("Cleanup failed")
            )

            with patch("app.modules.token_monitoring.scheduler.logger") as mock_logger:
                await scheduler._run_expiration_check()

                # Should log cleanup error but continue
                mock_logger.error.assert_called()
                error_call = mock_logger.error.call_args[0][0]
                assert "Failed to clean up old notifications" in error_call

    @pytest.mark.asyncio
    async def test_run_expiration_check_error_handling(
        self, scheduler, mock_expiration_service
    ):
        """Test error handling in expiration check."""
        mock_expiration_service.check_token_expiration.side_effect = Exception(
            "Database error"
        )

        with patch("app.modules.token_monitoring.scheduler.logger") as mock_logger:
            await scheduler._run_expiration_check()

            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            assert "Failed to run token expiration check" in error_call

    @pytest.mark.asyncio
    async def test_run_manual_check(self, scheduler, mock_expiration_service):
        """Test manual token expiration check."""
        expected_stats = {"total_tokens_checked": 5, "notifications_sent": 1}
        mock_expiration_service.check_token_expiration.return_value = expected_stats

        with patch("app.modules.token_monitoring.scheduler.logger") as mock_logger:
            result = await scheduler.run_manual_check()

            assert result == expected_stats
            mock_expiration_service.check_token_expiration.assert_called_once()
            mock_logger.info.assert_called_with("Running manual token expiration check")

    @pytest.mark.asyncio
    async def test_get_expiring_tokens_report(self, scheduler, mock_expiration_service):
        """Test getting expiring tokens report."""
        expected_report = {"tokens_expiring_soon": 3, "total_warnings": 7}
        mock_expiration_service.get_expiring_tokens_summary.return_value = (
            expected_report
        )

        result = await scheduler.get_expiring_tokens_report(14)

        assert result == expected_report
        mock_expiration_service.get_expiring_tokens_summary.assert_called_once_with(14)

    @pytest.mark.asyncio
    async def test_get_expiring_tokens_report_default_days(
        self, scheduler, mock_expiration_service
    ):
        """Test getting expiring tokens report with default days."""
        await scheduler.get_expiring_tokens_report()

        mock_expiration_service.get_expiring_tokens_summary.assert_called_once_with(30)


class TestSchedulerGlobalFunctions:
    """Test global scheduler functions."""

    @pytest.mark.asyncio
    async def test_get_token_monitoring_scheduler_singleton(self):
        """Singleton factory returns one TokenMonitoringScheduler without TG env.

        Bare construction pulls NotificationManager → get_notification_sender →
        settings.TG_TOKENS_FOR_SENDING. Patch the sender seam so the test does
        not require developer TG_TOKENS_FOR_SENDING while still exercising the
        real get_token_monitoring_scheduler singleton path.
        """
        import app.modules.token_monitoring.scheduler as scheduler_mod
        from app.client_bot.notification_sender import reset_notification_sender

        scheduler_mod._scheduler_instance = None
        try:
            with patch(
                "app.modules.token_monitoring.services.notification_manager.get_notification_sender",
                return_value=MagicMock(name="notification_sender"),
            ):
                scheduler1 = get_token_monitoring_scheduler()
                scheduler2 = get_token_monitoring_scheduler()

            assert scheduler1 is scheduler2
            assert isinstance(scheduler1, TokenMonitoringScheduler)
        finally:
            scheduler_mod._scheduler_instance = None
            reset_notification_sender()

    @pytest.mark.asyncio
    async def test_start_token_monitoring_scheduler(self):
        """Test starting global scheduler."""
        with patch(
            "app.modules.token_monitoring.scheduler.get_token_monitoring_scheduler"
        ) as mock_get:
            mock_scheduler = AsyncMock(return_value=None)
            mock_get.return_value = mock_scheduler

            check_time = time(11, 0)
            await start_token_monitoring_scheduler(check_time)

            mock_scheduler.start_daily_expiration_check.assert_called_once_with(
                check_time
            )

    @pytest.mark.asyncio
    async def test_start_token_monitoring_scheduler_default_time(self):
        """Test starting global scheduler with default time."""
        with patch(
            "app.modules.token_monitoring.scheduler.get_token_monitoring_scheduler"
        ) as mock_get:
            mock_scheduler = AsyncMock(return_value=None)
            mock_get.return_value = mock_scheduler

            await start_token_monitoring_scheduler()

            mock_scheduler.start_daily_expiration_check.assert_called_once_with(
                time(9, 0)
            )

    @pytest.mark.asyncio
    async def test_stop_token_monitoring_scheduler(self):
        """Test stopping global scheduler."""
        with patch(
            "app.modules.token_monitoring.scheduler.get_token_monitoring_scheduler"
        ) as mock_get:
            mock_scheduler = AsyncMock(return_value=None)
            mock_get.return_value = mock_scheduler

            await stop_token_monitoring_scheduler()

            mock_scheduler.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_manual_token_check(self):
        """Test running manual token check via global function."""
        with patch(
            "app.modules.token_monitoring.scheduler.get_token_monitoring_scheduler"
        ) as mock_get:
            mock_scheduler = AsyncMock(return_value=None)
            expected_result = {"checked": 10, "notified": 2}
            mock_scheduler.run_manual_check.return_value = expected_result
            mock_get.return_value = mock_scheduler

            result = await run_manual_token_check()

            assert result == expected_result
            mock_scheduler.run_manual_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token_expiration_report(self):
        """Test getting token expiration report via global function."""
        with patch(
            "app.modules.token_monitoring.scheduler.get_token_monitoring_scheduler"
        ) as mock_get:
            mock_scheduler = AsyncMock(return_value=None)
            expected_report = {"expiring": 5, "total": 20}
            mock_scheduler.get_expiring_tokens_report.return_value = expected_report
            mock_get.return_value = mock_scheduler

            result = await get_token_expiration_report(15)

            assert result == expected_report
            mock_scheduler.get_expiring_tokens_report.assert_called_once_with(15)

    @pytest.mark.asyncio
    async def test_get_token_expiration_report_default_days(self):
        """Test getting token expiration report with default days."""
        with patch(
            "app.modules.token_monitoring.scheduler.get_token_monitoring_scheduler"
        ) as mock_get:
            mock_scheduler = AsyncMock(return_value=None)
            mock_get.return_value = mock_scheduler

            await get_token_expiration_report()

            mock_scheduler.get_expiring_tokens_report.assert_called_once_with(30)
