import pytest

from app.modules.wb_adv_updater.modules.balance_exp_informer.dto import ReminderItem
from app.modules.wb_adv_updater.modules.balance_exp_informer.levels import BalanceLevel
from app.modules.wb_adv_updater.modules.balance_exp_informer.message_builder import (
    build_message,
    sort_items,
)


@pytest.mark.unit
def test_title_only_expired() -> None:
    msg, _kb = build_message(
        [
            ReminderItem(
                reminder_id=1,
                wb_cabinet_id=10,
                shop_name="integration-shop",
                level=int(BalanceLevel.EXPIRED),
                balance=0.0,
                avg_daily_spend=100.0,
                days_left=0.0,
            )
        ]
    )

    assert msg.splitlines()[0] == "🔴 Деньги закончились"
    assert "integration-shop" in msg


@pytest.mark.unit
def test_title_mixed_expired_and_low() -> None:
    msg, _kb = build_message(
        [
            ReminderItem(
                reminder_id=1,
                wb_cabinet_id=10,
                shop_name="shop-a",
                level=int(BalanceLevel.EXPIRED),
                balance=0.0,
                avg_daily_spend=100.0,
                days_left=-1.0,
            ),
            ReminderItem(
                reminder_id=2,
                wb_cabinet_id=11,
                shop_name="shop-b",
                level=int(BalanceLevel.D1),
                balance=50.0,
                avg_daily_spend=100.0,
                days_left=0.2,
            ),
        ]
    )

    assert msg.splitlines()[0] == "🔴 Деньги закончились"
    assert "❌ shop-a: деньги закончились" in msg
    assert "⚠️ shop-b: осталось меньше суток" in msg


@pytest.mark.unit
def test_d1_message_is_less_than_day() -> None:
    msg, _kb = build_message(
        [
            ReminderItem(
                reminder_id=1,
                wb_cabinet_id=10,
                shop_name="shop",
                level=int(BalanceLevel.D1),
                balance=10.0,
                avg_daily_spend=100.0,
                days_left=0.2,
            )
        ]
    )

    assert msg.splitlines()[0] == "🟡 Деньги заканчиваются"
    assert "⚠️ shop: осталось меньше суток" in msg
    assert "0 дн." not in msg


@pytest.mark.unit
def test_sort_items_expired_first_then_d1_then_d3() -> None:
    items = [
        ReminderItem(
            reminder_id=1,
            wb_cabinet_id=10,
            shop_name="b",
            level=int(BalanceLevel.D3),
            balance=0.0,
            avg_daily_spend=100.0,
            days_left=2.0,
        ),
        ReminderItem(
            reminder_id=2,
            wb_cabinet_id=11,
            shop_name="a",
            level=int(BalanceLevel.D1),
            balance=0.0,
            avg_daily_spend=100.0,
            days_left=0.8,
        ),
        ReminderItem(
            reminder_id=3,
            wb_cabinet_id=12,
            shop_name="c",
            level=int(BalanceLevel.EXPIRED),
            balance=0.0,
            avg_daily_spend=100.0,
            days_left=-0.1,
        ),
    ]

    sorted_items = sort_items(items)
    assert [it.level for it in sorted_items] == [
        int(BalanceLevel.EXPIRED),
        int(BalanceLevel.D1),
        int(BalanceLevel.D3),
    ]


@pytest.mark.unit
def test_title_only_d3() -> None:
    msg, _kb = build_message(
        [
            ReminderItem(
                reminder_id=1,
                wb_cabinet_id=10,
                shop_name="shop-d3",
                level=int(BalanceLevel.D3),
                balance=300.0,
                avg_daily_spend=100.0,
                days_left=2.2,
            )
        ]
    )

    assert msg.splitlines()[0] == "🟢 Деньги заканчиваются"
    assert "⏳ shop-d3: осталось меньше 3 дней" in msg
