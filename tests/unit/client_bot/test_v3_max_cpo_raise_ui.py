"""Unit: V3 Raise MAX Telegram UI helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.v3_max_cpo_raise_ui import (
    v3_substitute_fact_cpo_main_button,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.buttoms import (
    sales_plan_button,
)


@pytest.mark.unit
def test_v3_raise_toggle_button_text() -> None:
    adv = SimpleNamespace(id=1, v3_substitute_fact_cpo_for_max=False)
    btn = v3_substitute_fact_cpo_main_button(adv)
    assert "выкл" in btn.text
    adv_on = SimpleNamespace(id=1, v3_substitute_fact_cpo_for_max=True)
    btn_on = v3_substitute_fact_cpo_main_button(adv_on)
    assert "вкл" in btn_on.text


@pytest.mark.unit
def test_sales_plan_button_shows_raise_suffix() -> None:
    adv = SimpleNamespace(
        adv_id=10,
        plan_for_sales_for_day=100,
        target_price_for_order=80.0,
        max_price_for_order=120.0,
        v3_substitute_fact_cpo_for_max=True,
    )
    btn = sales_plan_button.get(adv, fact_pay_for_order=150.0)
    assert "120 → 150" in btn.text
