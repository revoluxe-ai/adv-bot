"""Scenario seam S15: production notify_shelf_exhausted_pause → Telegram send.

Uses shared ContractCase ``asep.telegram.shelf_exhausted_notify.v1`` and
recording sender; does not assert builder-only without send contract.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.messages import (
    build_shelf_exhausted_pause_message,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.notify import (
    notify_shelf_exhausted_pause,
)
from tests.unit.auto_shelf_exhausted_pause.telegram_notify_contract import (
    CONTRACT_ID,
    NOTIFY_CASE_ADV_SETTING_ID,
    NOTIFY_CASE_CAMPAIGN_NAME,
    NOTIFY_CASE_CHAT_ID,
    NOTIFY_CASE_DUE_AT,
    NOTIFY_CASE_RESOLVE_CPO_KIND,
    NOTIFY_CASE_RESOLVE_CPO_VALUE,
    NOTIFY_CASE_SHOP_NAME,
    TELEGRAM_NOTIFY_CASES,
    RecordingTelegramNotificationSender,
)

_LOAD_CHAT_IDS = (
    "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager."
    "exhausted_pause.notify.load_telegram_chat_ids_for_shop"
)


def _session_cm(fake_session: object) -> MagicMock:
    """Async context manager yielding ``fake_session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s15_notify_enter_sends_html_parse_mode_contract() -> None:
    """S15 scenario_seam: enter-notify path with production notify function."""
    assert CONTRACT_ID == "asep.telegram.shelf_exhausted_notify.v1"
    case = TELEGRAM_NOTIFY_CASES[0]
    sender = RecordingTelegramNotificationSender()
    sm_mock = MagicMock(return_value=_session_cm(object()))
    expected_text = build_shelf_exhausted_pause_message(
        shop_name=NOTIFY_CASE_SHOP_NAME,
        campaign_name=NOTIFY_CASE_CAMPAIGN_NAME,
        resolve_cpo_kind=NOTIFY_CASE_RESOLVE_CPO_KIND,
        resolve_cpo_value=NOTIFY_CASE_RESOLVE_CPO_VALUE,
        due_at=NOTIFY_CASE_DUE_AT,
    )
    assert "<b>" in expected_text
    # why/when/CPO must appear in production message text
    assert "250" in expected_text or "250.0" in expected_text

    with patch(_LOAD_CHAT_IDS, new=AsyncMock(return_value={NOTIFY_CASE_CHAT_ID})):
        delivered = await notify_shelf_exhausted_pause(
            shop_id="shop-html",
            adv_id=501,
            shop_name=NOTIFY_CASE_SHOP_NAME,
            campaign_name=NOTIFY_CASE_CAMPAIGN_NAME,
            resolve_cpo_kind=NOTIFY_CASE_RESOLVE_CPO_KIND,
            resolve_cpo_value=NOTIFY_CASE_RESOLVE_CPO_VALUE,
            due_at=NOTIFY_CASE_DUE_AT,
            adv_setting_original_id=NOTIFY_CASE_ADV_SETTING_ID,
            notification_sender=sender,  # type: ignore[arg-type]
            session_maker=sm_mock,
        )

    assert delivered is True
    sender.assert_matches_case(case, expected_text=expected_text)
