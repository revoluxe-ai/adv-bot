import pytest

from app.modules.wb_adv_updater.modules.balance_exp_informer.dto import ReminderItem
from app.modules.wb_adv_updater.modules.balance_exp_informer.levels import (
    BalanceLevel,
    pick_level,
)
from app.modules.wb_adv_updater.modules.balance_exp_informer.message_builder import (
    build_message,
    chunk,
    sort_items,
)


def _make_reminder(level: int, days_left: float, name: str) -> ReminderItem:
    return ReminderItem(
        reminder_id=0,
        wb_cabinet_id=1,
        shop_name=name,
        level=level,
        balance=0.0,
        avg_daily_spend=1.0,
        days_left=days_left,
    )


@pytest.mark.parametrize(
    ("days_left", "expected"),
    [
        (-0.1, BalanceLevel.EXPIRED),
        (0, BalanceLevel.EXPIRED),
        (0.9, BalanceLevel.D1),
        (1.0, BalanceLevel.D1),
        (1.5, BalanceLevel.D3),
        (3.0, BalanceLevel.D3),
        (3.01, None),
    ],
)
def test_pick_level_boundaries(days_left, expected):
    assert pick_level(days_left) == expected


def test_sort_items_prioritizes_levels():
    expired = _make_reminder(BalanceLevel.EXPIRED, -1.0, "expired")
    d1 = _make_reminder(BalanceLevel.D1, 0.5, "d1")
    d3 = _make_reminder(BalanceLevel.D3, 2.0, "d3")
    ordered = sort_items([d3, d1, expired])
    assert ordered[0].level == BalanceLevel.EXPIRED
    assert ordered[1].level == BalanceLevel.D1
    assert ordered[2].level == BalanceLevel.D3


def test_chunk_splits_into_twelfth_groups():
    items = [_make_reminder(BalanceLevel.D3, i, f"shop-{i}") for i in range(25)]
    splitted = chunk(items)
    assert len(splitted[0]) <= 12
    assert sum(len(block) for block in splitted) == len(items)
    assert len(splitted) == 3


def test_build_message_buttons_match_items():
    items = [_make_reminder(BalanceLevel.D1, 0.5, f"shop-{i}") for i in range(3)]
    text, keyboard = build_message(items)
    assert "⚠️" in text
    assert keyboard.inline_keyboard
    assert len(keyboard.inline_keyboard) == len(items)

