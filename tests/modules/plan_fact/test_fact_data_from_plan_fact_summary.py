"""Unit tests for fact_data_from_plan_fact_summary (plan_fact_reader)."""

from unittest.mock import MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactSummary,
    fact_data_from_plan_fact_summary,
)


@pytest.mark.unit
def test_fact_data_from_plan_fact_summary_none_summary() -> None:
    adv = MagicMock()
    adv.sales_predict_method = FactMethods.DIRECT_SALES
    assert fact_data_from_plan_fact_summary(None, adv) is None


@pytest.mark.unit
def test_fact_data_from_plan_fact_summary_none_predict() -> None:
    adv = MagicMock()
    adv.sales_predict_method = FactMethods.DIRECT_SALES
    summary = PlanFactSummary(
        adv_id=1,
        fact_predict_orders=None,
        fact_pay_for_order=50.0,
    )
    assert fact_data_from_plan_fact_summary(summary, adv) is None


@pytest.mark.unit
def test_fact_data_from_plan_fact_summary_full_row() -> None:
    adv = MagicMock()
    adv.sales_predict_method = FactMethods.BY_CARTS
    summary = PlanFactSummary(
        adv_id=1,
        fact_predict_orders=95.5,
        fact_pay_for_order=520.123,
        fact_original_orders=90.0,
        fact_method="DIRECT_SALES",
    )
    fact = fact_data_from_plan_fact_summary(summary, adv)
    assert fact is not None
    assert fact.predict_orders == 95.5
    assert fact.pay_for_order == 520.12
    assert fact.original_orders == 90.0
    assert FactMethods(fact.fact_method) == FactMethods.DIRECT_SALES


@pytest.mark.unit
def test_fact_data_from_plan_fact_summary_fallback_original_to_predict() -> None:
    adv = MagicMock()
    adv.sales_predict_method = FactMethods.DIRECT_SALES
    summary = PlanFactSummary(
        adv_id=1,
        fact_predict_orders=42.0,
        fact_pay_for_order=None,
        fact_original_orders=None,
        fact_method=None,
    )
    fact = fact_data_from_plan_fact_summary(summary, adv)
    assert fact is not None
    assert fact.original_orders == 42.0
    assert FactMethods(fact.fact_method) == FactMethods.DIRECT_SALES


@pytest.mark.unit
def test_fact_data_from_plan_fact_summary_invalid_method_uses_adv() -> None:
    adv = MagicMock()
    adv.sales_predict_method = FactMethods.BY_CARTS
    summary = PlanFactSummary(
        adv_id=1,
        fact_predict_orders=1.0,
        fact_pay_for_order=None,
        fact_original_orders=1.0,
        fact_method="NOT_A_REAL_METHOD",
    )
    fact = fact_data_from_plan_fact_summary(summary, adv)
    assert fact is not None
    assert FactMethods(fact.fact_method) == FactMethods.BY_CARTS
