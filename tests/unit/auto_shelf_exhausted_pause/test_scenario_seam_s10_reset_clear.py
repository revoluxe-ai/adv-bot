"""Scenario seam S10: reset pause button → clear PG block; no forced start_auto."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.user_interface.handlers import auto_shelf_bid_control_menu as handler
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service import (
    AutoShelfBidControlTelegramService,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from tests.unit.auto_shelf_exhausted_pause.asep_activity_helpers import (
    make_state,
    run_ensure_with_shelf_state,
)
from tests.unit.auto_shelf_exhausted_pause.wb_pause_auto_contract import (
    WB_PAUSE_AUTO_CASES,
    RecordingWbAutoLifecycle,
)


class _FakeMessage:
    """Message double for ``_tg_message`` isinstance narrowing.

    Production handler looks up ``Message`` in its module globals; tests patch
    that symbol to this class (same pattern as menu_handler suite).
    """

    def __init__(self) -> None:
        self.answers: list[str] = []

    async def answer(self, text: str, **kwargs: object) -> None:
        self.answers.append(text)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s10_reset_button_clears_via_telegram_service_no_forced_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S10: production TelegramService.clear → handler; Auto stays paused under blocker.

    Does not stop at FakeService AsyncMock-only: real
    ``AutoShelfBidControlTelegramService.clear_shelf_exhausted_pause`` runs with
    injectable repository.
    """
    monkeypatch.setattr(handler, "Message", _FakeMessage)

    repo = MagicMock()
    repo.get_adv_setting_by_original_id = AsyncMock(
        return_value=SimpleNamespace(id=99, nmids=[9001], nmid=9001)
    )
    repo.clear_shelf_exhausted_pause = AsyncMock(return_value=True)

    real_service = AutoShelfBidControlTelegramService(
        redis_client=MagicMock(),
        repository=repo,
    )
    # Adv shape for _get_single_nmid_or_raise
    monkeypatch.setattr(
        AutoShelfBidControlTelegramService,
        "_get_single_nmid_or_raise",
        staticmethod(lambda adv: 9001),
    )

    callback_message = _FakeMessage()
    callback = SimpleNamespace(data="asb_exh_reset:99", message=callback_message)

    monkeypatch.setattr(
        handler,
        "AutoShelfBidControlTelegramService",
        lambda **_: real_service,
    )

    await handler.auto_shelf_exhausted_reset_pause(
        callback=callback,  # type: ignore[arg-type]
        redis_client=MagicMock(),  # type: ignore[arg-type]
    )

    repo.clear_shelf_exhausted_pause.assert_awaited_once_with(9001)
    assert any("Снят только блок паузы" in a for a in callback_message.answers)

    # Other blocker still holds Auto: no forced start after clear.
    wb = RecordingWbAutoLifecycle()
    await run_ensure_with_shelf_state(
        wb=wb,
        state=make_state(pause_active=False),
        auto_status=WBAdvActiveStatus.PAUSE,
        spend_today=500.0,
        auto_budget_daily_limit=100,
    )
    start_case = next(
        c
        for c in WB_PAUSE_AUTO_CASES
        if c.case_id == "start_auto_forbidden_other_blocker"
    )
    wb.assert_matches_case(start_case)
