"""Unit: notify_empty_keywords_pause → Telegram send_message (injectable sender).

Causal Redis debounce (fakeredis mark_notified) + message build stay real;
PG cabinets lookup stubbed after debounce so send_message is exercised.
Does not patch away notify_empty_keywords_pause itself.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.intent import (
    EmptyKeywordsPauseIntentManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.messages import (
    build_empty_keywords_pause_message,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.notify import (
    notify_empty_keywords_pause,
)
from tests.unit.auto_updater_v3.empty_keywords_pause.notify_empty_keywords_contract import (
    NOTIFY_TELEGRAM_BOUNDARY_CASE,
    assert_notify_kwargs_match_case,
)


def _session_cm(fake_session: object) -> MagicMock:
    """Async context manager yielding ``fake_session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_sends_telegram_via_injected_sender(
    fake_redis: FakeRedis,
) -> None:
    """mark_notified OK → cabinets fake → notification_sender.send_message."""
    case = NOTIFY_TELEGRAM_BOUNDARY_CASE
    sender = MagicMock()
    sender.send_message = AsyncMock(return_value=True)
    sm_mock = MagicMock(return_value=_session_cm(object()))
    expected = build_empty_keywords_pause_message(
        campaign_name=case.campaign_name,
        adv_id=case.adv_id,
        include_support_link=True,
    )

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3"
            ".empty_keywords_pause.notify.load_telegram_chat_ids_for_shop",
            new=AsyncMock(return_value={555001}),
        ),
    ):
        intent = EmptyKeywordsPauseIntentManager()
        await notify_empty_keywords_pause(
            **case.as_required_kwargs(),
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )

    assert_notify_kwargs_match_case(case.as_required_kwargs(), case)
    sm_mock.assert_called_once_with(read_only=True)
    sender.send_message.assert_awaited_once()
    call = sender.send_message.await_args
    assert call is not None
    assert call.args[0] == 555001
    assert call.args[1] == expected
    assert call.kwargs.get("disable_web_page_preview") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_debounce_skips_second_send_message(
    fake_redis: FakeRedis,
) -> None:
    """Второй вход с тем же adv_id: mark_notified False → send_message не вызывается."""
    sender = MagicMock()
    sender.send_message = AsyncMock(return_value=True)
    sm_mock = MagicMock(return_value=_session_cm(object()))

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3"
            ".empty_keywords_pause.notify.load_telegram_chat_ids_for_shop",
            new=AsyncMock(return_value={555001}),
        ),
    ):
        intent = EmptyKeywordsPauseIntentManager()
        case = NOTIFY_TELEGRAM_BOUNDARY_CASE
        kwargs = dict(
            **case.as_required_kwargs(),
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )
        await notify_empty_keywords_pause(**kwargs)
        await notify_empty_keywords_pause(**kwargs)

    assert sender.send_message.await_count == 1
    assert sm_mock.call_count == 1
