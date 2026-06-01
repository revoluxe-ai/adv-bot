from __future__ import annotations

import pytest

from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    format_bid,
)

pytestmark = pytest.mark.unit


def test_format_bid_rub_displays_rubles_not_kopecks() -> None:
    assert format_bid(20_000, "RUB") == "200 ₽"
    assert format_bid(500, "RUB") == "5 ₽"


def test_format_bid_none() -> None:
    assert format_bid(None, "RUB") == "—"
