"""Unit tests for auto_shelf_bid_control strategy enum handling."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv.complex_adv import (
    resolve_auto_shelf_bid_control_strategy,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, AutoShelfBidControlStrategy.PLAN_DISTANCE),
        ("", ""),
        ("unknown", "unknown"),
        (AutoShelfBidControlStrategy.PLAN_DISTANCE, AutoShelfBidControlStrategy.PLAN_DISTANCE),
    ],
)
def test_resolve_auto_shelf_bid_control_strategy(
    raw_value: AutoShelfBidControlStrategy | str | None,
    expected: AutoShelfBidControlStrategy | str,
) -> None:
    """Рефакторинг оставил enum-путь для None и passthrough для заданных значений."""
    assert resolve_auto_shelf_bid_control_strategy(raw_value) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, AutoShelfBidControlStrategy.PLAN_DISTANCE),
        ("", ""),
        ("unknown", "unknown"),
        (AutoShelfBidControlStrategy.PLAN_DISTANCE, AutoShelfBidControlStrategy.PLAN_DISTANCE),
    ],
)
def test_complex_adv_exposes_auto_shelf_bid_control_strategy(
    raw_value: AutoShelfBidControlStrategy | str | None,
    expected: AutoShelfBidControlStrategy | str,
) -> None:
    """ComplexAdv отдает значение из AdvSetting без изменения семантики рефакторинга."""
    adv_setting = MagicMock()
    adv_setting.auto_shelf_bid_control_strategy = raw_value
    complex_adv = ComplexAdv(adv_setting=adv_setting)

    assert complex_adv.auto_shelf_bid_control_strategy == expected
