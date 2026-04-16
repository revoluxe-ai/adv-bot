"""Unit-тесты Excel roundtrip (план/факт KPI и парсинг)."""

import math

import pytest

from app.client_bot.user_interface.services.adv_excel_roundtrip.deviation import (
    compute_deviation_metrics,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EXCEL_TEMPLATE_VERSION,
    parse_edit_value,
    parse_header,
)


@pytest.mark.unit
def test_deviation_score_euclidean() -> None:
    # plan 10 orders, fact 5 -> -0.5; target cost 100, fact 200 -> +1.0
    d = compute_deviation_metrics(
        fact_orders_per_day=5.0,
        plan_orders_per_day=10,
        fact_cost_per_order=200.0,
        target_cost_per_order=100.0,
    )
    assert d.orders_dev_pct == pytest.approx(-0.5)
    assert d.cost_dev_pct == pytest.approx(1.0)
    assert d.deviation_score == pytest.approx(math.sqrt(0.5**2 + 1.0**2))


@pytest.mark.unit
def test_deviation_none_when_plan_missing() -> None:
    d = compute_deviation_metrics(
        fact_orders_per_day=5.0,
        plan_orders_per_day=None,
        fact_cost_per_order=100.0,
        target_cost_per_order=100.0,
    )
    assert d.orders_dev_pct is None
    assert d.cost_dev_pct == pytest.approx(0.0)
    assert d.deviation_score == pytest.approx(0.0)


@pytest.mark.unit
def test_parse_header_edit_bool() -> None:
    k, f, s = parse_header("EDIT__bot_active__BOOL")
    assert k == "EDIT"
    assert f == "bot_active"
    assert s == "BOOL"


@pytest.mark.unit
def test_parse_edit_bool_from_excel() -> None:
    assert parse_edit_value("bot_active", True) is True
    assert parse_edit_value("bot_active", "FALSE") is False


@pytest.mark.unit
def test_template_version_constant() -> None:
    assert EXCEL_TEMPLATE_VERSION >= 1
