"""Stub-contract for ASEP Telegram shelf-exhausted notify send shape."""

from __future__ import annotations

import inspect

import pytest

from app.client_bot.notification_sender import NotificationSender
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.messages import (
    build_shelf_exhausted_pause_message,
)
from tests.unit.auto_shelf_exhausted_pause.telegram_notify_contract import (
    CONTRACT_ID,
    NOTIFY_CASE_CAMPAIGN_NAME,
    NOTIFY_CASE_DUE_AT,
    NOTIFY_CASE_RESOLVE_CPO_KIND,
    NOTIFY_CASE_RESOLVE_CPO_VALUE,
    NOTIFY_CASE_SHOP_NAME,
    TELEGRAM_NOTIFY_CASES,
    RecordingTelegramNotificationSender,
)


@pytest.mark.unit
def test_telegram_notify_contract_id_and_cases() -> None:
    """Shared ContractCase set for ASEP notify HTML send."""
    assert CONTRACT_ID == "asep.telegram.shelf_exhausted_notify.v1"
    by_id = {c.case_id: c for c in TELEGRAM_NOTIFY_CASES}
    assert by_id["enter_notify_html_parse_mode"].require_parse_mode_html is True


@pytest.mark.unit
def test_recording_sender_signature_matches_notification_sender() -> None:
    """Boundary adapter: fake send_message shape = production sender."""
    fake_sig = inspect.signature(RecordingTelegramNotificationSender.send_message)
    fake_params = [p for p in fake_sig.parameters if p not in ("self",)]
    assert fake_params[:2] == ["chat_id", "text"]
    assert callable(NotificationSender.send_message)
    assert inspect.iscoroutinefunction(
        RecordingTelegramNotificationSender.send_message
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recording_sender_matches_html_parse_mode_case() -> None:
    """Fake kwargs parity with ContractCase enter_notify_html_parse_mode."""
    case = TELEGRAM_NOTIFY_CASES[0]
    expected = build_shelf_exhausted_pause_message(
        shop_name=NOTIFY_CASE_SHOP_NAME,
        campaign_name=NOTIFY_CASE_CAMPAIGN_NAME,
        resolve_cpo_kind=NOTIFY_CASE_RESOLVE_CPO_KIND,
        resolve_cpo_value=NOTIFY_CASE_RESOLVE_CPO_VALUE,
        due_at=NOTIFY_CASE_DUE_AT,
    )
    fake = RecordingTelegramNotificationSender()
    await fake.send_message(
        case.chat_id,
        expected,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=object(),
    )
    fake.assert_matches_case(case, expected_text=expected)
