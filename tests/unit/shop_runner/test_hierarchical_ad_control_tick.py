"""Shop-runner вызывает read-only diagnostics и молчит, пока флаг выключен."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.manager import CoroutinesManager

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_diagnostics_coroutine_is_idle_when_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Флаг читается из env; выключенное значение не вызывает live-read."""
    runner = AsyncMock()
    monkeypatch.setenv("HIERARCHICAL_AD_CONTROL_DIAGNOSTICS_ENABLED", "false")
    monkeypatch.setattr(
        "app.modules.shop_runner.hierarchical_ad_control_diagnostics.run_enabled_shop_diagnostics",
        runner,
    )
    manager = MagicMock()
    manager.shop_id = "shop"
    await CoroutinesManager.hierarchical_ad_control_diagnostics.__wrapped__(manager)
    runner.assert_not_called()


@pytest.mark.asyncio
async def test_diagnostics_coroutine_runs_once_when_flag_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Включённый флаг вызывает ровно один read-only прогон магазина."""
    runner = AsyncMock()
    monkeypatch.setenv("HIERARCHICAL_AD_CONTROL_DIAGNOSTICS_ENABLED", "true")
    monkeypatch.setattr(
        "app.modules.shop_runner.hierarchical_ad_control_diagnostics.run_enabled_shop_diagnostics",
        runner,
    )
    manager = MagicMock()
    manager.shop_id = "shop-1"
    manager._wb_manager_hub.wb_data_manager.reports_manager = object()
    await CoroutinesManager.hierarchical_ad_control_diagnostics.__wrapped__(manager)
    runner.assert_awaited_once()
    kwargs = runner.await_args.kwargs
    assert kwargs["shop_id"] == "shop-1"
    assert kwargs["reports_manager"] is manager._wb_manager_hub.wb_data_manager.reports_manager
