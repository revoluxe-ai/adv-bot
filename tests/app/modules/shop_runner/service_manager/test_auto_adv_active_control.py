from typing import Awaitable, Callable
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)


class _FakeAdvSetting:
    def __init__(self, active_status: str, adv_id: int | None = None):
        self.active_status = active_status
        self.adv_id = adv_id


class _FakeSearchAdv:
    def __init__(self, active_status: str, adv_id: int | None = None):
        self.active_status = active_status
        self.adv_id = adv_id


class _FakeComplexAdv:
    def __init__(
        self,
        auto_limit: int,
        auto_status: str,
        search_limit: int,
        search_status: str,
        auto_adv_id: int | None = None,
        search_adv_id: int | None = None,
        *,
        bot_active: bool = True,
        watchdog_enabled: bool = True,
    ):
        self.bot_active = bot_active
        self.auto_budget_watchdog_enabled = watchdog_enabled
        self._auto_budget_daily_limit = auto_limit
        self._search_auto_budget_daily_limit = search_limit
        self._adv_setting = _FakeAdvSetting(active_status=auto_status, adv_id=auto_adv_id)
        self.search_adv = _FakeSearchAdv(active_status=search_status, adv_id=search_adv_id)
        self.shop_id = "shop-1"

    @property
    def adv_setting(self):
        return self._adv_setting

    @property
    def auto_budget_daily_limit(self) -> int:
        return self._auto_budget_daily_limit

    @property
    def search_auto_budget_daily_limit(self) -> int:
        return self._search_auto_budget_daily_limit


@pytest.mark.asyncio
async def test_auto_adv_active_control_service_starts_and_pauses_campaigns():
    adv_to_start = _FakeComplexAdv(
        auto_limit=100,
        auto_status="pause",
        search_limit=50,
        search_status="pause",
        auto_adv_id=1,
        search_adv_id=2,
    )
    adv_to_pause = _FakeComplexAdv(
        auto_limit=0,
        auto_status="started",
        search_limit=0,
        search_status="started",
        auto_adv_id=3,
        search_adv_id=4,
    )
    ignored_adv = _FakeComplexAdv(
        auto_limit=100,
        auto_status="pause",
        search_limit=0,
        search_status="started",
        auto_adv_id=5,
        search_adv_id=6,
        watchdog_enabled=False,
    )

    wb_modifier = MagicMock()
    wb_modifier.start_auto_campaign = AsyncMock()
    wb_modifier.pause_auto_campaign = AsyncMock()
    wb_modifier.start_auction_campaign = AsyncMock()
    wb_modifier.pause_auction_campaign = AsyncMock()

    run_tasks_call: dict[str, object] = {}

    async def mock_run_tasks(handlers: list[Callable[[], Awaitable[None]]], *args, **kwargs):
        run_tasks_call["tasks_manager"] = kwargs.get("tasks_manager")
        results = []
        for handler in handlers:
            results.append(await handler())
        return results

    http_tasks_manager = MagicMock()
    service = AutoAdvActiveControlService(
        wb_modifier=wb_modifier,
        tasks_manager=http_tasks_manager,
    )

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_adv_active_control.auto_adv_active_control_service.run_tasks",
        new=mock_run_tasks,
    ):
        await service.ensure_campaigns_active(
            [adv_to_start, adv_to_pause, ignored_adv]
        )

    wb_modifier.start_auto_campaign.assert_awaited_once_with(adv_to_start)
    wb_modifier.start_auction_campaign.assert_awaited_once_with(adv_to_start)
    wb_modifier.pause_auto_campaign.assert_awaited_once_with(adv_to_pause)
    wb_modifier.pause_auction_campaign.assert_awaited_once_with(adv_to_pause)
    assert run_tasks_call["tasks_manager"] is http_tasks_manager
