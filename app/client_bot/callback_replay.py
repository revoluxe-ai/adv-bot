"""Helpers for storing and replaying blocked callback queries through FSM state."""

from __future__ import annotations

import json
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery, Update


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
    if event.from_user is not None:
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
        payload["message"] = {
            "message_id": _json_scalar(getattr(event.message, "message_id", 0), 0),
            "date": (
                int(event.message.date.timestamp())
                if getattr(event.message, "date", None) is not None
                else 0
            ),
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
    dispatcher: Dispatcher,
    bot: Bot,
    serialized_callback: str,
    *,
    update_id: int,
) -> None:
    """Replay a previously serialized callback query through the dispatcher."""
    callback_query = CallbackQuery.model_validate(json.loads(serialized_callback))
    replay_update = Update(update_id=update_id, callback_query=callback_query)
    await dispatcher.feed_update(bot, replay_update)
