from __future__ import annotations

from dataclasses import replace

from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    build_auto_shelf_bid_control_keyboard,
    build_auto_shelf_bid_settings_keyboard,
    render_auto_shelf_bid_control_message,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
    OptimizationMetric,
)


def _view(*, enabled: bool, has_settings: bool) -> AutoShelfBidControlViewDTO:
    return AutoShelfBidControlViewDTO(
        nmid=111,
        auto_adv_id=222,
        enabled=enabled,
        has_settings=has_settings,
        has_state=False,
        dry_run=True,
        bid_units_confirmed=False,
        actual_bid_minor=None,
        min_bid_minor=None,
        max_bid_minor=500,
        current_main_bid_minor=None,
        current_test_bid_minor=None,
        cycle_best_bid_minor=None,
        global_best_bid_minor=None,
        next_test_bid_minor=None,
        currency="RUB",
        current_mode=None,
        current_cycle_started_at=None,
        test_started_at=None,
        main_started_at=None,
        test_share=0.1,
        target_test_impressions=500,
        target_test_observation_minutes=60,
        target_main_impressions=4500,
        target_main_observation_minutes=540,
        min_bid_distance_minor=10,
        test_impressions=None,
        main_impressions=None,
        test_elapsed_minutes=None,
        main_elapsed_minutes=None,
        covered_points_count=0,
        bid_points_total=0,
        bid_points=[],
        cycle_covered_points_count=0,
        cycle_bid_points=[],
        last_reason=None,
        warnings=[],
        optimization_metric=OptimizationMetric.CPC,
        fact_cpo=None,
        resolve_cpo=None,
    )


def _keyboard_texts(markup: object) -> list[str]:
    keyboard = getattr(markup, "inline_keyboard")
    return [button.text for row in keyboard for button in row]


def test_main_keyboard_disabled_has_enable_settings_refresh_back() -> None:
    markup = build_auto_shelf_bid_control_keyboard(
        _view(enabled=False, has_settings=False),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert texts == ["Включить управление", "Настройки", "Обновить", "Назад"]


def test_main_keyboard_disabled_has_enable_settings_refresh_back_when_settings_exist() -> None:
    markup = build_auto_shelf_bid_control_keyboard(
        _view(enabled=False, has_settings=True),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert texts == ["Включить управление", "Настройки", "Обновить", "Назад"]


def test_main_keyboard_enabled_has_disable_reset_force_main() -> None:
    markup = build_auto_shelf_bid_control_keyboard(
        _view(enabled=True, has_settings=True),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert texts == [
        "Выключить управление",
        "Настройки",
        "Обновить",
        "Сбросить цикл",
        "Вернуть main-ставку",
        "Назад",
    ]


def test_main_keyboard_shows_cycle_coverage_button_when_state_exists() -> None:
    view = replace(_view(enabled=True, has_settings=True), has_state=True)
    markup = build_auto_shelf_bid_control_keyboard(view, adv_setting_original_id=1)
    texts = _keyboard_texts(markup)
    assert "Покрытия цикла" in texts


def test_settings_keyboard_contains_all_actions() -> None:
    markup = build_auto_shelf_bid_settings_keyboard(adv_setting_original_id=1)
    texts = _keyboard_texts(markup)
    assert texts == [
        "Изменить max ставку",
        "Изменить долю теста",
        "Изменить показов на тест",
        "Изменить минут теста",
        "Изменить шаг между ставками",
        "Назад к управлению ставкой",
    ]


def test_render_main_message_without_rec_bid_recommendation() -> None:
    view = _view(enabled=True, has_settings=True)

    message = render_auto_shelf_bid_control_message(view)

    assert "🧪 Рекомендации по ставке полок" not in message


def test_render_main_message_with_rec_bid_recommendation() -> None:
    view = replace(
        _view(enabled=True, has_settings=True),
        rec_bid_recommendation={
            "best_expected_bid": 123,
            "best_plan_bid": 456,
            "diagnostics": {
                "hour_observation_count": 7,
                "bid_count": 3,
            },
            "plan_ranked": [
                {
                    "bid": 10,
                    "ctr": 0.1,
                    "expected_order_cost_rub": 11.1,
                    "resolved_order_cost_rub": 22.2,
                    "sales_gap": -3.0,
                    "plan_distance_score": 0.5,
                },
                {
                    "bid": 20,
                    "ctr": 0.2,
                    "expected_order_cost_rub": 33.3,
                    "resolved_order_cost_rub": 44.4,
                    "sales_gap": -2.0,
                    "plan_distance_score": 0.4,
                },
                {
                    "bid": 30,
                    "ctr": 0.3,
                    "expected_order_cost_rub": 55.5,
                    "resolved_order_cost_rub": 66.6,
                    "sales_gap": -1.0,
                    "plan_distance_score": 0.3,
                },
            ],
            "expected_ranked": [
                {
                    "bid": 10,
                    "expected_daily_impressions": 1000.0,
                    "confidence": 0.9,
                    "own_anchor": 0.1,
                },
                {
                    "bid": 20,
                    "expected_daily_impressions": 2000.0,
                    "confidence": 0.8,
                    "own_anchor": 0.2,
                },
                {
                    "bid": 30,
                    "expected_daily_impressions": 3000.0,
                    "confidence": 0.7,
                    "own_anchor": 0.3,
                },
            ],
        },
    )

    message = render_auto_shelf_bid_control_message(view)

    assert "🧪 Рекомендации по ставке полок" in message
    assert "best_expected_bid: 123" in message
    assert "best_plan_bid: 456" in message
    assert "hours: 7" in message
    assert "bids: 3" in message
    assert "Top-3 plan_ranked:" in message
    assert "Top-3 expected_ranked:" in message
