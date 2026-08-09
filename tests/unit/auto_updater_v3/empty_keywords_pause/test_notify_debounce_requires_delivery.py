"""ROOT-001: notify debounce must not stick without confirmed delivery.

Bug (notify.py): ``mark_notified`` (Redis SET NX, 24h) must not permanently
consume the debounce window when ``shop_id`` / chat_ids / ``send_message``
skip or fail. Skipped or failed delivery must leave debounce free so a later
successful notify in the same window can deliver.

Expected: after empty shop_id skip, empty chat_ids, or ``send_message`` False,
a subsequent notify with valid preconditions MUST still deliver.

Promoted from CASE results/RED-ROOT-001/; patterns adapted from
``test_notify_telegram.py`` (FakeRedis + injectable sender).
"""

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

TEST_ID = "ROOT-001::test_notify_debounce_not_consumed_when_empty_shop_id_skips_delivery"

_NOTIFY_LOAD_CHAT_IDS = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3"
    ".empty_keywords_pause.notify.load_telegram_chat_ids_for_shop"
)


def _session_cm(fake_session: object) -> MagicMock:
    """Async context manager yielding ``fake_session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_debounce_not_consumed_when_empty_shop_id_skips_delivery(
    fake_redis: FakeRedis,
) -> None:
    """Empty shop_id skip must not block a later successful notify (same TTL).

    Given: first ``notify_empty_keywords_pause`` with empty ``shop_id``
    (delivery skipped, debounce not consumed).
    When: second call with valid shop_id + chat_ids + send_message True.
    Then: ``send_message`` MUST be awaited (debounce must not remain consumed).
    """
    sender = MagicMock()
    sender.send_message = AsyncMock(return_value=True)
    sm_mock = MagicMock(return_value=_session_cm(object()))
    adv_id = 9001
    campaign_name = "РК Empty Notify Debounce"

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(
            _NOTIFY_LOAD_CHAT_IDS,
            new=AsyncMock(return_value={555001}),
        ),
    ):
        intent = EmptyKeywordsPauseIntentManager()
        await notify_empty_keywords_pause(
            shop_id="",
            adv_id=adv_id,
            campaign_name=campaign_name,
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )
        # Delivery skipped; debounce must remain retryable.
        notify_key = intent._notify_key(adv_id)
        key_after_skip = await fake_redis.get(notify_key)

        await notify_empty_keywords_pause(
            shop_id="shop-tg-1",
            adv_id=adv_id,
            campaign_name=campaign_name,
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )

    assert sender.send_message.await_count == 1, (
        f"{TEST_ID}: after empty shop_id skip, later successful notify must "
        f"call send_message once; got await_count={sender.send_message.await_count}. "
        f"notify_key_after_skip={key_after_skip!r} (None expected if debounce "
        f"released; non-None means mark_notified consumed before delivery)."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_debounce_not_consumed_when_no_chat_ids(
    fake_redis: FakeRedis,
) -> None:
    """No telegram chat_ids must not block a later successful notify."""
    sender = MagicMock()
    sender.send_message = AsyncMock(return_value=True)
    sm_mock = MagicMock(return_value=_session_cm(object()))
    adv_id = 9002
    campaign_name = "РК No Chat Ids"

    load_chat_ids = AsyncMock(side_effect=[{}, {555002}])

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(_NOTIFY_LOAD_CHAT_IDS, new=load_chat_ids),
    ):
        intent = EmptyKeywordsPauseIntentManager()
        kwargs = dict(
            shop_id="shop-tg-2",
            adv_id=adv_id,
            campaign_name=campaign_name,
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )
        await notify_empty_keywords_pause(**kwargs)
        await notify_empty_keywords_pause(**kwargs)

    assert sender.send_message.await_count == 1, (
        "ROOT-001::test_notify_debounce_not_consumed_when_no_chat_ids: "
        "after empty chat_ids skip, later notify with chat_ids must deliver; "
        f"got await_count={sender.send_message.await_count}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_debounce_not_consumed_when_send_message_fails(
    fake_redis: FakeRedis,
) -> None:
    """send_message False must not leave debounce stuck for the next attempt."""
    sender = MagicMock()
    sender.send_message = AsyncMock(side_effect=[False, True])
    sm_mock = MagicMock(return_value=_session_cm(object()))
    adv_id = 9003
    campaign_name = "РК Send Fail"

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(
            _NOTIFY_LOAD_CHAT_IDS,
            new=AsyncMock(return_value={555003}),
        ),
    ):
        intent = EmptyKeywordsPauseIntentManager()
        kwargs = dict(
            shop_id="shop-tg-3",
            adv_id=adv_id,
            campaign_name=campaign_name,
            notification_sender=sender,
            intent_manager=intent,
            session_maker=sm_mock,
        )
        await notify_empty_keywords_pause(**kwargs)
        await notify_empty_keywords_pause(**kwargs)

    assert sender.send_message.await_count == 2, (
        "ROOT-001::test_notify_debounce_not_consumed_when_send_message_fails: "
        "after send_message False, retry in same window must call send_message "
        f"again; got await_count={sender.send_message.await_count}"
    )
    # Second delivery must succeed (not suppressed by debounce).
    assert sender.send_message.await_args_list[-1].args[0] == 555003
