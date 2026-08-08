"""Mock-only: PG PURE_READ handoff для notify_empty_keywords_pause.

Доказывает: parent открывает session_maker(read_only=True) и передаёт
ту же session в load_telegram_chat_ids_for_shop. Не live PG.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.notify import (
    load_telegram_chat_ids_for_shop,
    notify_empty_keywords_pause,
)


def _session_cm(fake_session: object) -> MagicMock:
    """Async context manager yielding ``fake_session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_opens_sm_read_only_true_and_hands_off_session() -> None:
    """Parent MUST call session_maker(read_only=True) and pass session to child."""
    fake_session = object()
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    intent = MagicMock()
    intent.mark_notified = AsyncMock(return_value=True)
    sender = MagicMock()
    sender.send_message = AsyncMock(return_value=True)
    load_mock = AsyncMock(return_value={4242})

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3"
        ".empty_keywords_pause.notify.load_telegram_chat_ids_for_shop",
        new=load_mock,
    ):
        await notify_empty_keywords_pause(
            shop_id="shop-pg-1",
            adv_id=9001,
            campaign_name="Test",
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )

    sm_mock.assert_called_once_with(read_only=True)
    load_mock.assert_awaited_once_with(fake_session, "shop-pg-1")
    sender.send_message.assert_awaited_once()
    assert sender.send_message.await_args is not None
    assert sender.send_message.await_args.args[0] == 4242


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_telegram_chat_ids_extracts_tg_from_cabinets() -> None:
    """Child maps WBUserCabinet.user.user_telegram_id → chat_ids."""
    session = MagicMock()
    user = MagicMock()
    user.user_telegram_id = 777
    uc = MagicMock()
    uc.user = user
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3"
        ".empty_keywords_pause.notify.get_wb_user_cabinets_for_shop",
        new=AsyncMock(return_value=[uc]),
    ) as cabinets_mock:
        chat_ids = await load_telegram_chat_ids_for_shop(session, "shop-x")

    cabinets_mock.assert_awaited_once_with(session, "shop-x")
    assert chat_ids == {777}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_skips_pg_when_debounce_blocks() -> None:
    """mark_notified=False → session_maker не вызывается."""
    sm_mock = MagicMock()
    intent = MagicMock()
    intent.mark_notified = AsyncMock(return_value=False)
    sender = MagicMock()
    sender.send_message = AsyncMock()

    await notify_empty_keywords_pause(
        shop_id="shop-pg-1",
        adv_id=9001,
        campaign_name="Test",
        notification_sender=sender,
        intent_manager=intent,
        session_maker=sm_mock,
    )

    sm_mock.assert_not_called()
    sender.send_message.assert_not_awaited()
