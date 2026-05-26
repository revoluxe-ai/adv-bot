from __future__ import annotations

from dataclasses import replace

from app.client_bot.user_interface.views.messages.auto_shelf_bid_control_render import (
    build_auto_shelf_bid_control_keyboard,
    build_auto_shelf_bid_settings_keyboard,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
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
        target_main_impressions=4500,
        min_bid_distance_minor=10,
        test_impressions=None,
        main_impressions=None,
        covered_points_count=0,
        bid_points_total=0,
        bid_points=[],
        cycle_covered_points_count=0,
        cycle_bid_points=[],
        last_reason=None,
        warnings=[],
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
        "Изменить шаг между ставками",
        "Назад к управлению ставкой",
    ]
