"""RED regression: shelf-exhausted notify MUST pass parse_mode=HTML.

Bug ROOT-001 / BUGCASE-ASEP-NOTIFY-HTML: ``build_shelf_exhausted_pause_message``
emits HTML ``<b>`` markup, but ``notify_shelf_exhausted_pause`` calls
``NotificationSender.send_message`` without ``parse_mode=\"HTML\"``, so Telegram
renders raw tags.

Fingerprint: ``shelf_exhausted_notify_html_without_parse_mode``.
LOC: exhausted_pause/notify.py:99 (send_message call site).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.messages import (
    build_shelf_exhausted_pause_message,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.notify import (
    notify_shelf_exhausted_pause,
)

_LOAD_CHAT_IDS = (
    "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager."
    "exhausted_pause.notify.load_telegram_chat_ids_for_shop"
)

_DUE = datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC)


def _session_cm(fake_session: object) -> MagicMock:
    """Async context manager yielding ``fake_session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_shelf_exhausted_pause_passes_html_parse_mode() -> None:
    """HTML message body MUST be sent with parse_mode=\"HTML\".

    Protects: paid Telegram notify for shelf-exhausted pause must not render
    raw ``<b>`` tags. Causal boundary is the ``send_message`` call site kwargs.
    """
    sender = MagicMock()
    sender.send_message = AsyncMock(return_value=True)
    sm_mock = MagicMock(return_value=_session_cm(object()))
    expected_text = build_shelf_exhausted_pause_message(
        shop_name="Shop <X>",
        campaign_name="Camp & Co",
        resolve_cpo_kind="max",
        resolve_cpo_value=250.0,
        due_at=_DUE,
    )

    with patch(_LOAD_CHAT_IDS, new=AsyncMock(return_value={424242})):
        delivered = await notify_shelf_exhausted_pause(
            shop_id="shop-html",
            adv_id=501,
            shop_name="Shop <X>",
            campaign_name="Camp & Co",
            resolve_cpo_kind="max",
            resolve_cpo_value=250.0,
            due_at=_DUE,
            adv_setting_original_id=77,
            notification_sender=sender,
            session_maker=sm_mock,
        )

    assert delivered is True
    assert "<b>" in expected_text
    sender.send_message.assert_awaited_once()
    call = sender.send_message.await_args
    assert call is not None
    assert call.args[0] == 424242
    assert call.args[1] == expected_text
    assert "<b>" in call.args[1]
    # Causal claim ROOT-001: parse_mode must accompany HTML markup.
    assert call.kwargs.get("parse_mode") == "HTML", (
        "ROOT-001::test_notify_shelf_exhausted_pause_passes_html_parse_mode: "
        "message text contains HTML <b> tags from messages builder, but "
        f"send_message kwargs omit parse_mode=HTML; kwargs={call.kwargs!r}"
    )
