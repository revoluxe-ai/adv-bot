"""Stub-contract: notify AsyncMock kwargs ↔ real notify_empty_keywords_pause."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.intent import (
    EmptyKeywordsPauseIntentManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.notify import (
    notify_empty_keywords_pause,
)
from tests.unit.auto_updater_v3.empty_keywords_pause.notify_empty_keywords_contract import (
    CONTRACT_ID,
    NOTIFY_AFTER_SEARCH_PAUSE_CASE,
    NOTIFY_PG_HANDOFF_CASE,
    NOTIFY_REQUIRED_KWONLY,
    NOTIFY_TELEGRAM_BOUNDARY_CASE,
    assert_notify_kwargs_match_case,
    assert_notify_mock_matches_case,
)


def _session_cm(fake_session: object) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.unit
def test_notify_contract_required_kwonly_stable() -> None:
    """Shared schema: shop_id / adv_id / campaign_name — production call shape."""
    assert CONTRACT_ID == "empty-keywords-notify-v1"
    assert NOTIFY_REQUIRED_KWONLY == frozenset(
        {"shop_id", "adv_id", "campaign_name"}
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recording_notify_mock_matches_activity_contract_case() -> None:
    """Scenario-side fake: kwargs shape equals NOTIFY_AFTER_SEARCH_PAUSE_CASE."""
    notify_mock = AsyncMock()
    case = NOTIFY_AFTER_SEARCH_PAUSE_CASE
    await notify_mock(**case.as_required_kwargs(), intent_manager=object())
    assert_notify_mock_matches_case(notify_mock, case, require_intent_manager=True)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_real_notify_accepts_telegram_boundary_contract_case(
    fake_redis: FakeRedis,
) -> None:
    """Boundary: real notify_empty_keywords_pause(**TELEGRAM_CASE.as_required_kwargs())."""
    case = NOTIFY_TELEGRAM_BOUNDARY_CASE
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
        await notify_empty_keywords_pause(
            **case.as_required_kwargs(),
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )

    assert_notify_kwargs_match_case(case.as_required_kwargs(), case)
    sender.send_message.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_real_notify_accepts_pg_handoff_contract_case() -> None:
    """Boundary: real notify accepts PG_HANDOFF_CASE kwargs (+ injectables)."""
    case = NOTIFY_PG_HANDOFF_CASE
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
            **case.as_required_kwargs(),
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )

    assert_notify_kwargs_match_case(case.as_required_kwargs(), case)
    sm_mock.assert_called_once_with(read_only=True)
    load_mock.assert_awaited_once_with(fake_session, case.shop_id)
