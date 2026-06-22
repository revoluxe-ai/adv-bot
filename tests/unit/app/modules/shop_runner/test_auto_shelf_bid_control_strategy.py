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
        ("", AutoShelfBidControlStrategy.PLAN_DISTANCE),
        ("unknown", AutoShelfBidControlStrategy.PLAN_DISTANCE),
        ("cycle_metric", AutoShelfBidControlStrategy.CPC),
        (AutoShelfBidControlStrategy.CYCLE_METRIC, AutoShelfBidControlStrategy.CPC),
        (AutoShelfBidControlStrategy.PLAN_DISTANCE, AutoShelfBidControlStrategy.PLAN_DISTANCE),
        ("ctr", AutoShelfBidControlStrategy.CTR),
        ("cpc", AutoShelfBidControlStrategy.CPC),
    ],
)
def test_resolve_auto_shelf_bid_control_strategy(
    raw_value: AutoShelfBidControlStrategy | str | None,
    expected: AutoShelfBidControlStrategy,
) -> None:
    """None, пустые и неизвестные значения должны падать в legacy default."""
    assert resolve_auto_shelf_bid_control_strategy(raw_value) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, AutoShelfBidControlStrategy.PLAN_DISTANCE),
        ("", AutoShelfBidControlStrategy.PLAN_DISTANCE),
        ("unknown", AutoShelfBidControlStrategy.PLAN_DISTANCE),
        ("cycle_metric", AutoShelfBidControlStrategy.CPC),
        (AutoShelfBidControlStrategy.PLAN_DISTANCE, AutoShelfBidControlStrategy.PLAN_DISTANCE),
        (AutoShelfBidControlStrategy.CTR, AutoShelfBidControlStrategy.CTR),
        (AutoShelfBidControlStrategy.CPC, AutoShelfBidControlStrategy.CPC),
    ],
)
def test_complex_adv_exposes_auto_shelf_bid_control_strategy(
    raw_value: AutoShelfBidControlStrategy | str | None,
    expected: AutoShelfBidControlStrategy,
) -> None:
    """ComplexAdv должен нормализовать control-strategy в enum default."""
    adv_setting = MagicMock()
    adv_setting.auto_shelf_bid_control_strategy = raw_value
    complex_adv = ComplexAdv(adv_setting=adv_setting)

    assert complex_adv.auto_shelf_bid_control_strategy == expected
