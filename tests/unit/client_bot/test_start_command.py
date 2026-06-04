"""Unit-тесты для app.client_bot.start_command."""

from unittest.mock import MagicMock

import pytest
from aiogram.types import Message

from app.client_bot.start_command import is_start_command_message, is_start_command_text


@pytest.mark.parametrize(
    "text",
    [
        "/start",
        "/START",
        "/Start",
        "/start@my_bot",
        "/START@My_Bot",
        "  /start  ",
        "/start payload",
    ],
)
def test_is_start_command_text_true(text: str) -> None:
    assert is_start_command_text(text) is True


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "   ",
        "\n\t",
        "/starting",
        "/startx",
        "hello",
        "/help",
    ],
)
def test_is_start_command_text_false(text: str | None) -> None:
    assert is_start_command_text(text) is False


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_is_start_command_message_empty_text_returns_false(text: str) -> None:
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.caption = None
    assert is_start_command_message(msg) is False


def test_is_start_command_message_uses_caption_when_text_missing() -> None:
    msg = MagicMock(spec=Message)
    msg.text = None
    msg.caption = "/Start"
    assert is_start_command_message(msg) is True


def test_is_start_command_message_prefers_text_over_caption() -> None:
    msg = MagicMock(spec=Message)
    msg.text = "/help"
    msg.caption = "/start"
    assert is_start_command_message(msg) is False
