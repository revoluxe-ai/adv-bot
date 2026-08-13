from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    build_auto_shelf_bid_control_keyboard,
    build_auto_shelf_bid_settings_keyboard,
    render_auto_shelf_bid_control_message,
)
from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    build_auto_shelf_bid_strategy_keyboard,
    render_auto_shelf_bid_strategy_message,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
    OptimizationMetric,
    CoverageLayerBidDTO,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)


def settings_keyboard_contains_all_actions_outdated() -> None:
    markup = build_auto_shelf_bid_settings_keyboard(
        _view(enabled=True, has_settings=True),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert texts == [
        "Режим main bid: Best plan",
        "Изменить max ставку",
        "Изменить долю теста",
        "Изменить показов на тест",
        "Изменить минут теста",
        "Изменить шаг между ставками",
        "Назад к управлению ставкой",
    ]


def test_strategy_keyboard_contains_only_strategy_actions() -> None:
    markup = build_auto_shelf_bid_strategy_keyboard(
        _view(enabled=True, has_settings=True),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert texts == ["✅ Best plan", "CTR", "CPC", "Назад к управлению ставкой"]


def test_render_strategy_message_shows_current_mode() -> None:
    message = render_auto_shelf_bid_strategy_message(
        _view(enabled=True, has_settings=True)
    )
    assert "Режим main bid" in message
    assert "Текущий режим: Best plan" in message


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
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
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


def legacy_settings_keyboard_contains_all_actions_legacy() -> None:
    markup = build_auto_shelf_bid_settings_keyboard(
        _view(enabled=True, has_settings=True),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert texts == [
        "✅ Best plan",
        "CTR",
        "CPC",
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
        fresh_best_main_bid_minor=35_000,
        fresh_next_test_bid_minor=20_500,
        rec_bid_recommendation={
            "best_expected_bid": 35000,
            "best_plan_bid": 35000,
            "diagnostics": {
                "hour_observation_count": 7,
                "bid_count": 3,
            },
            "plan_ranked": [
                {
                    "bid": 35000,
                    "expected_daily_impressions": 95818.2,
                    "expected_daily_clicks": 1396.6,
                    "expected_daily_orders": 69.83,
                    "cpo_rub": 568.0587841906347,
                    "cpc": 12.34,
                    "ctr": 0.01104280322383927,
                    "expected_order_cost_rub": 568.0587841906347,
                    "resolved_order_cost_rub": 550.0,
                    "sales_gap": -296.52,
                    "plan_distance_score": 0.835,
                },
                {
                    "bid": 16000,
                    "expected_daily_impressions": 12345.0,
                    "expected_daily_clicks": 245.76,
                    "expected_daily_orders": 12.34,
                    "cpo_rub": 123.45,
                    "ctr": 0.0199,
                    "expected_order_cost_rub": 123.45,
                    "sales_gap": -12.34,
                    "plan_distance_score": 0.456,
                },
                {
                    "bid": 20500,
                    "expected_daily_impressions": 54321.0,
                    "expected_daily_clicks": 1629.63,
                    "expected_daily_orders": 48.89,
                    "cpo_rub": 222.2,
                    "ctr": 0.03,
                    "expected_order_cost_rub": 222.2,
                    "sales_gap": -1.0,
                    "plan_distance_score": 0.3,
                },
            ],
            "expected_ranked": [
                {
                    "bid": 35000,
                    "expected_daily_impressions": 95818.2,
                    "confidence": 0.4918326535656478,
                    "own_anchor": 0.037878,
                },
                {
                    "bid": 16000,
                    "expected_daily_impressions": 12345.0,
                    "confidence": 0.8,
                    "own_anchor": 0.2,
                },
                {
                    "bid": 20500,
                    "expected_daily_impressions": 54321.0,
                    "confidence": 0.7,
                    "own_anchor": 0.3,
                },
            ],
        },
    )

    message = render_auto_shelf_bid_control_message(view)

    assert "\U0001f9ea \u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438 \u043f\u043e \u0441\u0442\u0430\u0432\u043a\u0435 \u043f\u043e\u043b\u043e\u043a" in message
    assert "best_expected_bid:" not in message
    assert "best_plan_bid:" not in message
    assert "hours:" not in message
    assert "bids:" not in message
    plan_ranked_block = message.split("Top-3 plan_ranked:\n", maxsplit=1)[1]
    assert "bid: 350 \u20bd" in plan_ranked_block
    assert "прогноз заказов/сутки: 69.83" in plan_ranked_block
    assert "CPO: 568.06 \u20bd" in plan_ranked_block
    assert "CTR: 1.10%" in plan_ranked_block
    assert "expected_daily_impressions:" not in plan_ranked_block
    assert "expected_daily_clicks:" not in plan_ranked_block
    assert "CPC:" not in plan_ranked_block
    assert "35000" not in message
    assert "568.0587841906347" not in message
    assert "Top-3 plan_ranked:" in message


def test_render_main_message_omits_missing_rec_fields_but_keeps_ctr() -> None:
    view = replace(
        _view(enabled=True, has_settings=True),
        rec_bid_recommendation={
            "plan_ranked": [
                {
                    "bid": 14_100,
                    "impressions": 1234,
                    "clicks": 56,
                    "carts": 7,
                    "orders": 3,
                    "spend": 255.4,
                    "cpc": 4.56,
                    "ctr": 0.0321,
                },
                {
                    "bid": 22_200,
                },
            ],
        },
    )

    message = render_auto_shelf_bid_control_message(view)

    plan_ranked_block = message.split("Top-3 plan_ranked:\n", maxsplit=1)[1]
    assert "bid: 141 \u20bd | показы 1 234 | CTR: 3.21%" in plan_ranked_block
    assert "прогноз заказов/сутки:" not in plan_ranked_block
    assert "expected_daily_orders: \u2014" not in plan_ranked_block
    assert "CPO: \u2014" not in plan_ranked_block
    assert "CPC:" not in plan_ranked_block


def test_render_main_message_formats_infinite_cpc_as_infinity_symbol() -> None:
    view = replace(
        _view(enabled=True, has_settings=True),
        rec_bid_recommendation={
            "plan_ranked": [
                {
                    "bid": 14_100,
                    "cpc": float("inf"),
                    "ctr": 0.0321,
                }
            ],
        },
    )

    message = render_auto_shelf_bid_control_message(view)

    plan_ranked_block = message.split("Top-3 plan_ranked:\n", maxsplit=1)[1]
    assert "CPC:" not in plan_ranked_block


def test_render_main_message_rejects_bool_best_plan_bid() -> None:
    view = replace(
        _view(enabled=True, has_settings=True),
        rec_bid_recommendation={
            "best_expected_bid": 35000,
            "best_plan_bid": True,
            "plan_ranked": [
                {
                    "bid": False,
                    "ctr": 0.011,
                    "expected_order_cost_rub": 568.05,
                    "resolved_order_cost_rub": 550.0,
                    "sales_gap": -296.52,
                    "plan_distance_score": 0.835,
                }
            ],
        },
        best_plan_bid_minor=None,
    )

    message = render_auto_shelf_bid_control_message(view)

    assert "best_plan_bid:" not in message
    assert "Лучшая плановая ставка:" not in message
    assert "bid: —" in message
    assert "CTR: 1.10%" in message
    assert "best_plan_bid: 1 ₽" not in message
    assert "bid: 0 ₽" not in message
    assert "0.01 ₽" not in message
    assert "1 minor" not in message
    assert "Лучшая плановая ставка:" not in message


def test_render_main_message_with_coverage_layers_block() -> None:
    view = replace(
        _view(enabled=True, has_settings=True),
        fresh_best_main_bid_minor=37_500,
        fresh_next_test_bid_minor=33_900,
        next_test_bid_minor=33_900,
        legacy_cycle_next_test_bid_minor=40_250,
        current_main_bid_minor=20_500,
        current_test_bid_minor=60_000,
        min_bid_minor=12_000,
        max_bid_minor=60_000,
        best_plan_bid_minor=37_500,
        coverage_first_available_bucket_start=datetime(2026, 5, 24, 21, 15, tzinfo=UTC),
        coverage_current_layer=0,
        coverage_undercovered_count=3,
        coverage_selected_next_test_bid_minor=33_900,
        coverage_bid_rows=[
            CoverageLayerBidDTO(
                label="current_main_bid_minor",
                bid_minor=20_500,
                impressions=184_393,
                valid_hours=184,
                closed_layers=92,
                undercovered=False,
                is_current_main=True,
            ),
            CoverageLayerBidDTO(
                label="current_test_bid_minor / selected_next_test_bid_minor",
                bid_minor=60_000,
                impressions=1_764,
                valid_hours=1,
                closed_layers=0,
                undercovered=True,
                is_current_test=True,
                is_selected_next_test=True,
            ),
            CoverageLayerBidDTO(
                label="best_plan_bid_minor",
                bid_minor=37_500,
                impressions=0,
                valid_hours=0,
                closed_layers=0,
                undercovered=True,
                is_best_plan=True,
            ),
        ],
    )

    message = render_auto_shelf_bid_control_message(view)

    assert "Покрытие ставок теста:" in message
    assert "Следующая тестовая ставка: 339 ₽" in message
    assert "first_available_bucket_start:" in message
    assert "current_layer: 0" in message
    assert "undercovered_count: 3" in message
    assert "selected_next_test_bid: 339 ₽" in message
    assert "402.50 ₽" not in message
    assert "Подробный список: в пагинированном просмотрщике." in message


def test_render_has_no_conflicting_historical_best_lines() -> None:
    view = replace(
        _view(enabled=True, has_settings=True),
        enabled=False,
        actual_bid_minor=57_000,
        fresh_best_main_bid_minor=57_000,
        fresh_next_test_bid_minor=41_000,
        current_main_bid_minor=48_000,
        cycle_best_bid_minor=48_000,
        global_best_bid_minor=20_500,
        best_plan_bid_minor=48_000,
        rec_bid_recommendation={
            "plan_ranked": [
                {"bid": 57_000, "plan_distance_score": 0.1},
                {"bid": 48_000, "plan_distance_score": 0.2},
                {"bid": 20_500, "plan_distance_score": 0.3},
            ],
        },
    )

    message = render_auto_shelf_bid_control_message(view)

    assert "Лучшая ставка: 570 ₽" in message
    assert "Следующая тестовая ставка: 410 ₽" in message
    assert "Top-3 plan_ranked:" in message
    assert "Лучшая ставка цикла" not in message
    assert "Лучшая глобальная ставка" not in message
    assert "Лучшая плановая ставка" not in message
    assert "Рабочая ставка main: 480 ₽" not in message
    assert "best_expected_bid" not in message
    assert "best_plan_bid" not in message


def test_render_ranking_consistency_shows_clamp_reason() -> None:
    view = replace(
        _view(enabled=True, has_settings=True),
        fresh_best_main_bid_minor=50_000,
        main_target_explanation="clamp_to_range: 57000 -> 50000",
        rec_bid_recommendation={
            "plan_ranked": [{"bid": 57_000}],
        },
    )

    message = render_auto_shelf_bid_control_message(view)

    assert "Лучшая ставка: 500 ₽" in message
    assert "clamp_to_range: 57000 -> 50000" in message
    assert message.count("clamp_to_range: 57000 -> 50000") == 1


def test_render_disabled_shows_recommended_main_without_dash() -> None:
    view = replace(
        _view(enabled=False, has_settings=True),
        has_state=True,
        recommended_main_bid_minor=57_000,
        fresh_best_main_bid_minor=57_000,
        primary_status="disabled",
        current_main_bid_minor=48_000,
        last_reason="main_waiting_observation_time",
        main_elapsed_minutes=10,
        target_main_observation_minutes=540,
        warnings=["no_actual_bid", "no_min_bid"],
        rec_bid_recommendation={
            "plan_ranked": [
                {"bid": 57_000},
                {"bid": 54_000},
                {"bid": 48_000},
            ],
        },
    )

    message = render_auto_shelf_bid_control_message(view)

    assert "Лучшая ставка: 570 ₽" in message
    assert "Лучшая ставка: —" not in message
    assert "main_waiting_observation_time" not in message.split("Последнее событие:")[1].split(
        "Предупреждения:"
    )[0]
    assert "disabled" in message


def test_render_enabled_no_actual_shows_recommended_not_not_applied() -> None:
    view = replace(
        _view(enabled=True, has_settings=True),
        has_state=True,
        recommended_main_bid_minor=57_000,
        fresh_best_main_bid_minor=57_000,
        expected_enforced_bid_minor=57_000,
        bid_sync_detail="no_actual_bid",
        actual_bid_minor=None,
        warnings=["no_actual_bid"],
        rec_bid_recommendation={"plan_ranked": [{"bid": 57_000}]},
    )

    message = render_auto_shelf_bid_control_message(view)

    assert "Лучшая ставка: 570 ₽" in message
    assert "НЕ применена" not in message
    assert "не применена" not in message.lower()


def test_insufficient_qualified_bids_render() -> None:
    """Render: no stale best bid, insufficient reason, next test bid shown."""
    view = replace(
        _view(enabled=True, has_settings=True),
        has_state=True,
        current_mode="test",
        current_main_bid_minor=48_000,
        actual_bid_minor=20_000,
        fresh_best_main_bid_minor=None,
        recommended_main_bid_minor=None,
        fresh_next_test_bid_minor=25_000,
        recommended_next_test_bid_minor=25_000,
        qualified_tested_bids_count=1,
        main_target_explanation="недостаточно протестированных ставок",
    )

    message = render_auto_shelf_bid_control_message(view)

    assert "Лучшая ставка: — (недостаточно протестированных ставок)" in message
    assert message.count("недостаточно протестированных ставок") == 1
    assert "Лучшая ставка: 480 ₽" not in message
    assert "Лучшая ставка: 570 ₽" not in message
    assert "Следующая тестовая ставка: 250 ₽" in message


def test_render_main_target_explanation_not_duplicated_when_main_bid_missing() -> None:
    """main_target_explanation рендерится ровно один раз при отсутствии main bid."""
    explanation = "недостаточно протестированных ставок"
    view = replace(
        _view(enabled=True, has_settings=True),
        has_state=True,
        current_mode="test",
        fresh_best_main_bid_minor=None,
        recommended_main_bid_minor=None,
        fresh_next_test_bid_minor=25_000,
        qualified_tested_bids_count=1,
        main_target_explanation=explanation,
    )

    message = render_auto_shelf_bid_control_message(view)

    assert f"Лучшая ставка: — ({explanation})" in message
    assert message.count(explanation) == 1
    assert f"({explanation})\n({explanation})" not in message
def test_settings_keyboard_contains_all_actions() -> None:
    markup = build_auto_shelf_bid_settings_keyboard(
        _view(enabled=True, has_settings=True),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert texts == [
        "Изменить max ставку",
        "Изменить долю теста",
        "Изменить показов на тест",
        "Изменить минут теста",
        "Изменить шаг между ставками",
        "Изменить интервал перетеста (сут)",
        "Назад к управлению ставкой",
    ]


def test_main_keyboard_shows_strategy_menu_on_upper_level() -> None:
    markup = build_auto_shelf_bid_control_keyboard(
        _view(enabled=True, has_settings=True),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert "Режим main bid: Best plan" in texts
def test_main_keyboard_disabled_has_enable_settings_refresh_back() -> None:
    markup = build_auto_shelf_bid_control_keyboard(
        _view(enabled=False, has_settings=False),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert texts == [
        "Включить управление",
        "Настройки",
        "Режим main bid: Best plan",
        "Обновить",
        "Назад",
    ]


def test_main_keyboard_disabled_has_enable_settings_refresh_back_when_settings_exist() -> None:
    markup = build_auto_shelf_bid_control_keyboard(
        _view(enabled=False, has_settings=True),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert texts == [
        "Включить управление",
        "Настройки",
        "Режим main bid: Best plan",
        "Обновить",
        "Назад",
    ]


def test_main_keyboard_enabled_has_disable_reset_force_main() -> None:
    markup = build_auto_shelf_bid_control_keyboard(
        _view(enabled=True, has_settings=True),
        adv_setting_original_id=1,
    )
    texts = _keyboard_texts(markup)
    assert texts == [
        "Выключить управление",
        "Настройки",
        "Режим main bid: Best plan",
        "Обновить",
        "Сбросить цикл",
        "Вернуть main-ставку",
        "Назад",
    ]
