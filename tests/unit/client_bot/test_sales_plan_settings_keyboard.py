"""Регрессия для UI плана продаж без лишнего fact pay_for_order."""

from types import SimpleNamespace

from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.buttoms import (
    sales_plan_button,
)
from app.modules.sales_plan_settings.telegram.keyboards import KeyboardsGetter


def test_sales_plan_button_text_depends_only_on_plan_fields() -> None:
    adv = SimpleNamespace(
        adv_id=1,
        plan_for_sales_for_day=None,
        target_price_for_order=None,
        max_price_for_order=None,
        substitute_fact_cpo_for_max=None,
    )

    button = sales_plan_button.get(adv)

    assert button.text == "⛔ План продаж Не установлен"


def test_sales_plan_settings_keyboard_ignores_fact_pfo_plumbing() -> None:
    adv = SimpleNamespace(
        adv_id=1,
        id=1,
        plan_for_sales_for_day=12,
        target_price_for_order=100,
        max_price_for_order=200,
        substitute_fact_cpo_for_max=None
    )

    keyboard = KeyboardsGetter().get_keyboard(adv)

    assert keyboard.inline_keyboard[0][0].text == "Изменить план продаж в день (12)"
    texts = [row[0].text for row in keyboard.inline_keyboard]
    assert "Включить RaisePlanOnPromobonuses" in texts
