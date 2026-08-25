"""ROOT-001 / task 9.2: resume/re-enable notify after empty-keywords pause.

Spec: ``User notification on empty-keywords resume/re-enable``.

After a **delivered** empty-keywords pause notify, when Search/keywords
resume or re-enable, production MUST emit a distinct resume/re-enable
Telegram notify to each shop-linked chat_id (same recipient scope as
pause fanout). Ordinary Search start without a prior delivered pause
notify episode MUST NOT send that resume notify.

Current production (gap): only ``notify_empty_keywords_pause`` + pause
message builder exist — no resume notify emit / message builder.
These tests MUST fail on unrepaired code (RED for ROOT-001).
"""

from __future__ import annotations

from typing import Any, Callable
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

TEST_ID_RESUME_FANOUT = (
    "tests/unit/auto_updater_v3/empty_keywords_pause/"
    "test_notify_resume_after_pause.py::"
    "test_resume_notify_send_message_for_each_shop_linked_chat_after_pause_episode"
)
TEST_ID_DISTINCT = (
    "tests/unit/auto_updater_v3/empty_keywords_pause/"
    "test_notify_resume_after_pause.py::"
    "test_resume_notify_text_distinct_from_pause_entry_and_recheck_mention"
)
TEST_ID_NO_PRIOR = (
    "tests/unit/auto_updater_v3/empty_keywords_pause/"
    "test_notify_resume_after_pause.py::"
    "test_no_resume_notify_without_prior_delivered_pause_episode"
)

_NOTIFY_LOAD_CHAT_IDS = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3"
    ".empty_keywords_pause.notify.load_telegram_chat_ids_for_shop"
)

_MULTI_CHAT_IDS: frozenset[int] = frozenset({555201, 555202})

_RESUME_GAP_HINT = (
    "ROOT-001 / task 9.2: empty-keywords resume/re-enable notify is missing "
    "(only notify_empty_keywords_pause + pause message builder exist)"
)


def _session_cm(fake_session: object) -> MagicMock:
    """Async context manager yielding ``fake_session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def _require_resume_notify() -> Callable[..., Any]:
    """Resolve resume notify emit; fail with gap reason if absent."""
    try:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.notify import (
            notify_empty_keywords_resume,
        )
    except ImportError as exc:
        pytest.fail(f"{_RESUME_GAP_HINT}: {exc}")
    return notify_empty_keywords_resume


def _require_resume_message_builder() -> Callable[..., str]:
    """Resolve resume message builder; fail with gap reason if absent."""
    try:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.messages import (
            build_empty_keywords_resume_message,
        )
    except ImportError as exc:
        pytest.fail(f"{_RESUME_GAP_HINT}: {exc}")
    return build_empty_keywords_resume_message


def _resume_calls(
    sender: MagicMock,
    *,
    pause_text: str,
) -> list[Any]:
    """``send_message`` awaits whose text is not the pause-entry payload."""
    out: list[Any] = []
    for call in sender.send_message.await_args_list:
        text = call.args[1] if len(call.args) > 1 else None
        if text != pause_text:
            out.append(call)
    return out


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resume_notify_send_message_for_each_shop_linked_chat_after_pause_episode(
    fake_redis: FakeRedis,
) -> None:
    """Delivered pause notify + resume → resume text to each shop-linked chat_id.

    Given: pause notify delivered to ≥2 chat_ids.
    When: resume/re-enable notify emit runs for the same episode.
    Then: each chat_id gets a resume message (≠ pause-entry).
    """
    notify_resume = _require_resume_notify()
    build_resume = _require_resume_message_builder()

    sender = MagicMock()
    sender.send_message = AsyncMock(return_value=True)
    sm_mock = MagicMock(return_value=_session_cm(object()))
    adv_id = 9201
    campaign_name = "РК Resume Fanout"
    shop_id = "shop-resume-fanout"
    pause_text = build_empty_keywords_pause_message(
        campaign_name=campaign_name,
        adv_id=adv_id,
        include_support_link=True,
    )
    expected_resume = build_resume(
        campaign_name=campaign_name,
        adv_id=adv_id,
        include_support_link=True,
    )

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(
            _NOTIFY_LOAD_CHAT_IDS,
            new=AsyncMock(return_value=set(_MULTI_CHAT_IDS)),
        ),
    ):
        intent = EmptyKeywordsPauseIntentManager()
        await notify_empty_keywords_pause(
            shop_id=shop_id,
            adv_id=adv_id,
            campaign_name=campaign_name,
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )
        pause_awaits = sender.send_message.await_count
        assert pause_awaits == len(_MULTI_CHAT_IDS), (
            f"{TEST_ID_RESUME_FANOUT}: pre-condition pause fanout failed; "
            f"await_count={pause_awaits}"
        )

        await notify_resume(
            shop_id=shop_id,
            adv_id=adv_id,
            campaign_name=campaign_name,
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )

    resume_calls = _resume_calls(sender, pause_text=pause_text)
    assert len(resume_calls) == len(_MULTI_CHAT_IDS), (
        f"{TEST_ID_RESUME_FANOUT}: expected resume send_message for each of "
        f"{sorted(_MULTI_CHAT_IDS)}; got {len(resume_calls)} resume call(s) "
        f"(total awaits={sender.send_message.await_count})"
    )
    resume_chat_ids = {call.args[0] for call in resume_calls}
    assert resume_chat_ids == set(_MULTI_CHAT_IDS), (
        f"{TEST_ID_RESUME_FANOUT}: resume chat_ids {sorted(resume_chat_ids)} "
        f"!= expected {sorted(_MULTI_CHAT_IDS)}"
    )
    for call in resume_calls:
        assert call.args[1] == expected_resume
        assert call.args[1] != pause_text
        assert call.kwargs.get("disable_web_page_preview") is True


@pytest.mark.unit
def test_resume_notify_text_distinct_from_pause_entry_and_recheck_mention() -> None:
    """Resume message MUST NOT equal pause-entry (recheck-mention ≠ resume)."""
    build_resume = _require_resume_message_builder()
    adv_id = 9202
    campaign_name = "РК Resume Distinct"
    pause_text = build_empty_keywords_pause_message(
        campaign_name=campaign_name,
        adv_id=adv_id,
        include_support_link=True,
    )
    resume_text = build_resume(
        campaign_name=campaign_name,
        adv_id=adv_id,
        include_support_link=True,
    )
    assert resume_text != pause_text, (
        f"{TEST_ID_DISTINCT}: resume text must be distinct from pause-entry; "
        "recheck-mention inside pause message is not a resume notify"
    )
    assert "empty_keywords" not in resume_text
    assert "EMPTY_KEYWORDS" not in resume_text
    # Resume/re-enable signal (not merely "перепровер" from pause-entry).
    lowered = resume_text.lower()
    assert any(
        token in lowered
        for token in ("возобнов", "включи", "снова", "resume", "re-enable", "включ")
    ), (
        f"{TEST_ID_DISTINCT}: resume text must signal resume/re-enable, "
        f"got: {resume_text!r}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_resume_notify_without_prior_delivered_pause_episode(
    fake_redis: FakeRedis,
) -> None:
    """Ordinary resume path without delivered pause notify → no resume send.

    Given: no prior delivered empty-keywords pause notify episode.
    When: resume/re-enable notify emit is invoked.
    Then: send_message MUST NOT be called for empty-keywords resume reason.
    """
    notify_resume = _require_resume_notify()

    sender = MagicMock()
    sender.send_message = AsyncMock(return_value=True)
    sm_mock = MagicMock(return_value=_session_cm(object()))
    adv_id = 9203
    campaign_name = "РК No Prior Pause"

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(
            _NOTIFY_LOAD_CHAT_IDS,
            new=AsyncMock(return_value=set(_MULTI_CHAT_IDS)),
        ),
    ):
        intent = EmptyKeywordsPauseIntentManager()
        await notify_resume(
            shop_id="shop-no-prior-pause",
            adv_id=adv_id,
            campaign_name=campaign_name,
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )

    assert sender.send_message.await_count == 0, (
        f"{TEST_ID_NO_PRIOR}: resume notify must not spam ordinary Search "
        f"start without prior delivered pause notify; got "
        f"await_count={sender.send_message.await_count}"
    )
