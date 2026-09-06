"""Helpers for storing and replaying blocked callback queries through FSM state."""

from __future__ import annotations

import itertools
import json
from datetime import datetime
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery, Update

_dispatcher: Dispatcher | None = None
# Отрицательные id — synthetic replay; не пересекаются с live Telegram update_id (>0).
_synthetic_update_id_counter = itertools.count(-1, -1)


def allocate_synthetic_update_id() -> int:
    """Выделить уникальный synthetic ``update_id`` для ``feed_update`` replay.

    Telegram ``update_id`` монotonic positive; replay после gate использует
    отрицательную монotonic-последовательность, чтобы не подставлять ``message_id``.
    """
    return next(_synthetic_update_id_counter)


def _json_scalar(value: Any, default: Any) -> Any:
    """Return a JSON-safe scalar value or the provided default."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return default


def serialize_callback_query(event: CallbackQuery) -> str:
    """Serialize the callback fields required to replay the same action later."""
    payload: dict[str, Any] = {
        "id": _json_scalar(getattr(event, "id", ""), ""),
        "chat_instance": _json_scalar(getattr(event, "chat_instance", ""), ""),
        "data": _json_scalar(getattr(event, "data", None), None),
    }
    # CallbackQuery.from_user is required User — always serialize.
    payload["from_user"] = {
        "id": event.from_user.id,
        "is_bot": _json_scalar(getattr(event.from_user, "is_bot", False), False),
        "first_name": _json_scalar(
            getattr(event.from_user, "first_name", "User"),
            "User",
        ),
        "username": _json_scalar(getattr(event.from_user, "username", None), None),
    }
    if event.message is not None:
        # MaybeInaccessibleMessage.date may be absent; only datetime has timestamp().
        date_raw = event.message.date
        date_unix = int(date_raw.timestamp()) if isinstance(date_raw, datetime) else 0
        payload["message"] = {
            "message_id": _json_scalar(getattr(event.message, "message_id", 0), 0),
            "date": date_unix,
            "chat": {
                "id": event.message.chat.id,
                "type": _json_scalar(
                    getattr(event.message.chat, "type", "private"),
                    "private",
                ),
            },
        }
    return json.dumps(payload)


async def replay_serialized_callback(
    bot: Bot,
    serialized_callback: str,
    *,
    dispatcher: Dispatcher | None = None,
) -> None:
    """Replay a previously serialized callback query through the dispatcher."""
    target_dispatcher = dispatcher or _dispatcher
    if target_dispatcher is None:
        raise RuntimeError("Dispatcher is not registered for callback replay.")
    callback_query = CallbackQuery.model_validate(json.loads(serialized_callback))
    replay_update = Update(
        update_id=allocate_synthetic_update_id(),
        callback_query=callback_query,
    )
    await target_dispatcher.feed_update(bot, replay_update)


def register_dispatcher(dispatcher: Dispatcher) -> None:
    """Register the active dispatcher for later callback replay."""
    global _dispatcher
    _dispatcher = dispatcher
