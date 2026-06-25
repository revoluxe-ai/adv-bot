"""Tests for TextWithKeyboardAndImage._split_caption."""

import pytest

from app.client_bot.const import TELEGRAM_CAPTION_LIMIT
from app.client_bot.user_interface.message_templates.templates import (
    TextWithKeyboardAndImage,
)


@pytest.mark.unit
def test_split_caption_short_unchanged() -> None:
    caption = "short"
    head, tail = TextWithKeyboardAndImage._split_caption(
        caption, limit=TELEGRAM_CAPTION_LIMIT
    )
    assert head == caption
    assert tail == ""


@pytest.mark.unit
def test_split_caption_no_gap_between_head_and_tail() -> None:
    limit = TELEGRAM_CAPTION_LIMIT
    suffix = "\n..."
    split_at = limit - len(suffix)
    caption = "a" * (limit + 100)
    head, tail = TextWithKeyboardAndImage._split_caption(caption, limit=limit)
    assert head.endswith(suffix)
    head_body = head[: -len(suffix)]
    assert head_body + tail == caption
    assert len(head) == limit
    assert tail.startswith("a")


@pytest.mark.unit
def test_split_caption_small_limit_no_suffix_branch() -> None:
    caption = "abcdefghijklmnop"
    head, tail = TextWithKeyboardAndImage._split_caption(caption, limit=10)
    assert head == caption[:10]
    assert tail == caption[10:]
