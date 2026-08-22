"""ROOT-001 / task 8.2: notify MUST fan out to all shop-linked chat_ids.

Owner ``B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS``: after
``notify_empty_keywords_pause``, ``send_message`` is awaited for **each**
distinct telegram chat_id from ``load_telegram_chat_ids_for_shop`` (≥2),
not only a single primary recipient.

Paired debounce (once-per-enter): KEEP when any delivery succeeds; RELEASE
when all ``send_message`` fail so a later attempt in the same window can
retry.
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

TEST_ID_FANOUT = (
    "tests/unit/auto_updater_v3/empty_keywords_pause/"
    "test_notify_multi_chat_fanout.py::"
    "test_notify_send_message_awaited_for_each_shop_linked_chat_id"
)
TEST_ID_KEEP = (
    "tests/unit/auto_updater_v3/empty_keywords_pause/"
    "test_notify_multi_chat_fanout.py::"
    "test_notify_multi_chat_debounce_keep_on_any_success"
)
TEST_ID_RELEASE = (
    "tests/unit/auto_updater_v3/empty_keywords_pause/"
    "test_notify_multi_chat_fanout.py::"
    "test_notify_multi_chat_debounce_release_on_all_fail"
)

_NOTIFY_LOAD_CHAT_IDS = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3"
    ".empty_keywords_pause.notify.load_telegram_chat_ids_for_shop"
)

_MULTI_CHAT_IDS: frozenset[int] = frozenset({555101, 555102})


def _session_cm(fake_session: object) -> MagicMock:
    """Async context manager yielding ``fake_session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_send_message_awaited_for_each_shop_linked_chat_id(
    fake_redis: FakeRedis,
) -> None:
    """≥2 distinct chat_ids → ``send_message`` awaited once per chat_id.

    Given: shop resolves two WBUserCabinet telegram chat_ids.
    When: ``notify_empty_keywords_pause`` runs with injectable sender.
    Then: each chat_id receives the same pause message (fanout, not one).
    """
    sender = MagicMock()
    sender.send_message = AsyncMock(return_value=True)
    sm_mock = MagicMock(return_value=_session_cm(object()))
    adv_id = 9101
    campaign_name = "РК Multi Chat Fanout"
    expected = build_empty_keywords_pause_message(
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
            shop_id="shop-multi-tg",
            adv_id=adv_id,
            campaign_name=campaign_name,
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )

    assert sender.send_message.await_count == len(_MULTI_CHAT_IDS), (
        f"{TEST_ID_FANOUT}: expected send_message for each of "
        f"{sorted(_MULTI_CHAT_IDS)}; got await_count="
        f"{sender.send_message.await_count}"
    )
    called_chat_ids = {
        call.args[0] for call in sender.send_message.await_args_list
    }
    assert called_chat_ids == set(_MULTI_CHAT_IDS), (
        f"{TEST_ID_FANOUT}: send_message chat_ids {sorted(called_chat_ids)} "
        f"!= expected {sorted(_MULTI_CHAT_IDS)}"
    )
    for call in sender.send_message.await_args_list:
        assert call.args[1] == expected
        assert call.kwargs.get("disable_web_page_preview") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_multi_chat_debounce_keep_on_any_success(
    fake_redis: FakeRedis,
) -> None:
    """Any successful delivery among multi chat_ids KEEP debounce (no retry)."""
    sender = MagicMock()
    # First chat fails, second succeeds → delivered=True → KEEP.
    sender.send_message = AsyncMock(side_effect=[False, True])
    sm_mock = MagicMock(return_value=_session_cm(object()))
    adv_id = 9102
    campaign_name = "РК Multi Keep Any"

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(
            _NOTIFY_LOAD_CHAT_IDS,
            new=AsyncMock(return_value=set(_MULTI_CHAT_IDS)),
        ),
    ):
        intent = EmptyKeywordsPauseIntentManager()
        kwargs = dict(
            shop_id="shop-multi-keep",
            adv_id=adv_id,
            campaign_name=campaign_name,
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )
        await notify_empty_keywords_pause(**kwargs)
        await notify_empty_keywords_pause(**kwargs)

    assert sender.send_message.await_count == len(_MULTI_CHAT_IDS), (
        f"{TEST_ID_KEEP}: after any-success KEEP, second notify must not "
        f"re-send; first attempt must still fan out to all chat_ids; "
        f"got await_count={sender.send_message.await_count}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_multi_chat_debounce_release_on_all_fail(
    fake_redis: FakeRedis,
) -> None:
    """All ``send_message`` False → RELEASE debounce; retry can fan out again."""
    sender = MagicMock()
    # Attempt 1: both fail. Attempt 2: both succeed.
    sender.send_message = AsyncMock(
        side_effect=[False, False, True, True],
    )
    sm_mock = MagicMock(return_value=_session_cm(object()))
    adv_id = 9103
    campaign_name = "РК Multi Release All"

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(
            _NOTIFY_LOAD_CHAT_IDS,
            new=AsyncMock(return_value=set(_MULTI_CHAT_IDS)),
        ),
    ):
        intent = EmptyKeywordsPauseIntentManager()
        kwargs = dict(
            shop_id="shop-multi-release",
            adv_id=adv_id,
            campaign_name=campaign_name,
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )
        await notify_empty_keywords_pause(**kwargs)
        await notify_empty_keywords_pause(**kwargs)

    expected_awaits = 2 * len(_MULTI_CHAT_IDS)
    assert sender.send_message.await_count == expected_awaits, (
        f"{TEST_ID_RELEASE}: after all-fail RELEASE, retry must fan out "
        f"again ({expected_awaits} awaits); got "
        f"{sender.send_message.await_count}"
    )
    retry_chat_ids = {
        call.args[0] for call in sender.send_message.await_args_list[2:]
    }
    assert retry_chat_ids == set(_MULTI_CHAT_IDS), (
        f"{TEST_ID_RELEASE}: retry fanout chat_ids {sorted(retry_chat_ids)} "
        f"!= expected {sorted(_MULTI_CHAT_IDS)}"
    )
