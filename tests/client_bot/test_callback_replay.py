"""Unit tests for synthetic callback replay update_id allocation."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.callback_replay import (
    allocate_synthetic_update_id,
    replay_serialized_callback,
)


pytestmark = pytest.mark.unit


def test_allocate_synthetic_update_id_is_negative_and_unique() -> None:
    first = allocate_synthetic_update_id()
    second = allocate_synthetic_update_id()
    assert first < 0
    assert second < 0
    assert first != second


@pytest.mark.asyncio
async def test_replay_serialized_callback_uses_synthetic_update_id() -> None:
    bot = MagicMock()
    dispatcher = MagicMock()
    dispatcher.feed_update = AsyncMock()
    payload = json.dumps(
        {
            "id": "cb-1",
            "chat_instance": "inst",
            "data": "test:data",
            "from_user": {
                "id": 42,
                "is_bot": False,
                "first_name": "User",
                "username": None,
            },
        }
    )

    await replay_serialized_callback(bot, payload, dispatcher=dispatcher)

    dispatcher.feed_update.assert_awaited_once()
    replay_update = dispatcher.feed_update.await_args.args[1]
    assert replay_update.update_id < 0
    assert replay_update.callback_query is not None
    assert replay_update.callback_query.data == "test:data"
