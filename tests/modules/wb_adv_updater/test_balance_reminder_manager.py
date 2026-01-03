"""Integration and unit tests for balance_expiration_informer_update function."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.wb_adv_updater.modules.balance_exp_informer.manager import (
    balance_expiration_informer_update,
    balance_expiration_informer_tick,
    CFG,
)


async def test_balance_expiration_informer_update_creates_service_and_loops():
    """Тест: функция создает сервис и вызывает tick в цикле."""
    with patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.BalanceReminderService"
    ) as mock_service_class, patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.session_factory"
    ) as mock_session_factory, patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.balance_expiration_informer_tick",
        new_callable=AsyncMock,
    ) as mock_tick:

        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        # Прерываем цикл на 2-й итерации
        mock_tick.side_effect = [None, asyncio.CancelledError]

        with pytest.raises(asyncio.CancelledError):
            await balance_expiration_informer_update()

        # Проверяем, что сервис создан с правильной session_factory
        mock_service_class.assert_called_once_with(mock_session_factory)
        
        # Проверяем, что tick вызывался 2 раза
        assert mock_tick.call_count == 2


async def test_balance_expiration_informer_tick_calls_service_update_in_send_window():
    """Тест: внутри окна отправки вызывается service.update()."""
    mock_service = AsyncMock()
    
    # 15:10 UTC — внутри окна [15, 18)
    send_hour = 15
    window_end_hour = 18
    current_time = datetime(2026, 1, 3, 15, 10, tzinfo=timezone.utc)

    with patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.datetime"
    ) as mock_datetime_module:
        mock_datetime_module.now.return_value = current_time
        mock_datetime_module.combine = datetime.combine
        mock_datetime_module.timezone = timezone
        
        with patch(
            "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
        
            cfg_in_window = type('CFG', (), {
                'send_hour_utc': send_hour,
                'window_end_hour_utc': window_end_hour,
                'fail_backoff_seconds': 60,
                'sleep_jitter_seconds': 10,
            })()

            await balance_expiration_informer_tick(mock_service, cfg_in_window)

            # Проверяем, что update был вызван
            mock_service.update.assert_awaited_once()
            
            # Проверяем, что затем произошел sleep
            mock_sleep.assert_awaited()


async def test_balance_expiration_informer_tick_sleeps_outside_send_window():
    """Тест: вне окна отправки функция спит до окна."""
    mock_service = AsyncMock()
    
    # 12:00 UTC — вне окна [15, 18)
    send_hour = 15
    window_end_hour = 18
    current_time = datetime(2026, 1, 3, 12, 0, tzinfo=timezone.utc)

    with patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.datetime"
    ) as mock_datetime_module:
        mock_datetime_module.now.return_value = current_time
        mock_datetime_module.combine = datetime.combine
        mock_datetime_module.timezone = timezone
        
        with patch(
            "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
        
            cfg_not_in_window = type('CFG', (), {
                'send_hour_utc': send_hour,
                'window_end_hour_utc': window_end_hour,
                'fail_backoff_seconds': 60,
                'sleep_jitter_seconds': 10,
            })()

            await balance_expiration_informer_tick(mock_service, cfg_not_in_window)

            # Проверяем, что update НЕ был вызван
            mock_service.update.assert_not_awaited()
            
            # Проверяем, что произошел sleep до окна
            mock_sleep.assert_awaited()


async def test_balance_expiration_informer_tick_handles_service_exception():
    """Тест: исключение в service.update() обрабатывается gracefully."""
    mock_service = AsyncMock()
    mock_service.update.side_effect = ValueError("Test error")
    
    # 15:10 UTC — внутри окна
    send_hour = 15
    window_end_hour = 18
    current_time = datetime(2026, 1, 3, 15, 10, tzinfo=timezone.utc)

    with patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.datetime"
    ) as mock_datetime_module:
        mock_datetime_module.now.return_value = current_time
        mock_datetime_module.combine = datetime.combine
        mock_datetime_module.timezone = timezone
        
        with patch(
            "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep, patch(
            "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.logger"
        ) as mock_logger:
        
            cfg_in_window = type('CFG', (), {
                'send_hour_utc': send_hour,
                'window_end_hour_utc': window_end_hour,
                'fail_backoff_seconds': 60,
                'sleep_jitter_seconds': 10,
            })()

            # Функция должна завершиться без исключения
            await balance_expiration_informer_tick(mock_service, cfg_in_window)

            # Проверяем, что исключение залогировано
            mock_logger.exception.assert_called_once()
            
            # Проверяем, что произошел backoff sleep
            mock_sleep.assert_awaited()


async def test_balance_expiration_informer_tick_uses_service_in_window():
    """Тест: при вызове tick с service - update выполняется в окне."""
    mock_service = AsyncMock()
    
    current_time = datetime(2026, 1, 3, 15, 30, tzinfo=timezone.utc)

    with patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.datetime"
    ) as mock_datetime_module:
        mock_datetime_module.now.return_value = current_time
        mock_datetime_module.combine = datetime.combine
        mock_datetime_module.timezone = timezone
        
        with patch(
            "app.modules.wb_adv_updater.modules.balance_exp_informer.manager.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
        
            await balance_expiration_informer_tick(mock_service)

            # Проверяем, что update вызван (находимся в окне [15, 18))
            mock_service.update.assert_awaited_once()
