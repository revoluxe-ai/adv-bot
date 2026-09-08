"""Unit: RaisePlanOnPromobonuses Telegram copy."""

from app.modules.sales_plan_settings.raise_plan_on_promobonuses import (
    format_raise_plan_on_promobonuses_toggle_message,
)


def test_toggle_message_lists_owner_labels() -> None:
    text = format_raise_plan_on_promobonuses_toggle_message(enabled=True)
    assert "RaisePlanOnPromobonuses" in text
    assert "PromoMaxCPO" in text
    assert "PromoTargetCPO" in text
    assert "PromoAutoBudget" in text
    assert "PropoSearchBudget" in text
    assert "PromoTarget Budget" in text
    off = format_raise_plan_on_promobonuses_toggle_message(enabled=False)
    assert "отключено" in off
