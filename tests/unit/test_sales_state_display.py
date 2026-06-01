"""Unit: отображение SalesStates и target_place в списке ключей."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state import (
    SALES_STATE_META,
    SalesStates,
    format_keyword_list_target_place_suffix,
    sales_state_short_label,
)
from app.client_bot.user_interface.utils.target_place_display import (
    format_target_place_display,
)


@pytest.mark.unit
def test_sales_state_meta_includes_all_states() -> None:
    for state in SalesStates:
        assert state in SALES_STATE_META


@pytest.mark.unit
def test_no_data_short_label() -> None:
    assert sales_state_short_label(SalesStates.NO_DATA) == "Н (Нет данных)"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tp", "expected"),
    [
        (None, "->Н>"),
        (0, "->0"),
        (5, "->5"),
    ],
)
def test_keyword_list_target_place_suffix(tp: int | None, expected: str) -> None:
    assert format_keyword_list_target_place_suffix(tp) == expected


@pytest.mark.unit
def test_format_target_place_zero_min_bid() -> None:
    value_str, _ = format_target_place_display(0, "individual")
    assert value_str == "0 (мин. ставка WB)"
