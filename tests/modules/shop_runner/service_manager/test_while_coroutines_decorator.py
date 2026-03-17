"""Tests for while_coroutine_decorator: shop_id in error logs and retry/sleep behavior."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.while_coroutines_decorator import (
    _get_shop_id_for_log,
    while_coroutine_decorator,
)

MODULE = "app.modules.shop_runner.service_manager.while_coroutines_decorator"


@pytest.mark.unit
def test_get_shop_id_for_log_from_self_shop_id() -> None:
    """When first arg has shop_id, it is returned."""
    obj = MagicMock()
    obj.shop_id = "12345"
    assert _get_shop_id_for_log((obj,)) == "12345"


@pytest.mark.unit
def test_get_shop_id_for_log_from_wb_api_fallback() -> None:
    """When first arg has _wb_api.shop_id but no shop_id, fallback is used."""
    obj = MagicMock(spec=[])
    del obj.shop_id
    obj._wb_api = MagicMock()
    obj._wb_api.shop_id = "999"
    assert _get_shop_id_for_log((obj,)) == "999"


@pytest.mark.unit
def test_get_shop_id_for_log_missing_self() -> None:
    """When args is empty, returns missing_shop_id(no_self)."""
    assert _get_shop_id_for_log(()) == "missing_shop_id(no_self)"


@pytest.mark.unit
def test_get_shop_id_for_log_missing_shop_id_includes_type() -> None:
    """When object has no shop_id and no _wb_api, returns missing_shop_id(type=...)."""
    class NoShopId:
        pass
    obj = NoShopId()
    result = _get_shop_id_for_log((obj,))
    assert "missing_shop_id" in result
    assert "NoShopId" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decorator_error_log_includes_shop_id_and_coroutine_name() -> None:
    """When wrapped coroutine raises, logger.error is called with shop_id and coroutine name."""
    decorator = while_coroutine_decorator(60, 5)
    async def failing_coro(self: object) -> None:
        raise ValueError("test error")
    wrapped = decorator(failing_coro)

    self_with_shop = MagicMock()
    self_with_shop.shop_id = "12345"

    with patch(f"{MODULE}.logger") as mock_logger:
        with patch(f"{MODULE}.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = Exception("stop_loop")
            with pytest.raises(Exception, match="stop_loop"):
                await wrapped(self_with_shop)

    mock_logger.error.assert_called_once()
    call_args = mock_logger.error.call_args
    assert call_args[0][1] == "12345"
    assert call_args[0][2] == "failing_coro"
    assert call_args[1]["exc_info"] is True
    mock_sleep.assert_called_with(5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decorator_error_log_includes_missing_shop_id_when_no_shop_id() -> None:
    """When first arg has no shop_id, log contains missing_shop_id(type=...)."""
    decorator = while_coroutine_decorator(60, 5)
    async def failing_coro(self: object) -> None:
        raise RuntimeError("x")
    wrapped = decorator(failing_coro)

    class NoShopId:
        pass
    self_no_shop = NoShopId()

    with patch(f"{MODULE}.logger") as mock_logger:
        with patch(f"{MODULE}.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = Exception("stop")
            with pytest.raises(Exception, match="stop"):
                await wrapped(self_no_shop)

    mock_logger.error.assert_called_once()
    shop_id_arg = mock_logger.error.call_args[0][1]
    assert "missing_shop_id" in shop_id_arg
    assert "NoShopId" in shop_id_arg


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decorator_sleep_and_retry_behavior_unchanged() -> None:
    """After exception: sleep(pause_on_error) is called; after success: sleep(pause_on_success)."""
    pause_on_success = 60
    pause_on_error = 5
    decorator = while_coroutine_decorator(pause_on_success, pause_on_error)
    call_count = 0

    async def raise_once_then_succeed(self: object) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("first call fails")
        return None

    wrapped = decorator(raise_once_then_succeed)
    self_mock = MagicMock()
    self_mock.shop_id = "1"

    sleep_calls: list[float] = []

    async def sleep_track_then_exit(secs: float) -> None:
        sleep_calls.append(secs)
        if len(sleep_calls) >= 2:
            raise Exception("exit_after_retry")

    with patch(f"{MODULE}.logger"):
        with patch(f"{MODULE}.asyncio.sleep", new_callable=AsyncMock, side_effect=sleep_track_then_exit):
            with pytest.raises(Exception, match="exit_after_retry"):
                await wrapped(self_mock)

    assert call_count == 2
    assert pause_on_error in sleep_calls
    assert pause_on_success in sleep_calls
