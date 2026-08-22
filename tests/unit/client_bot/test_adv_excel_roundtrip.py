"""Unit-тесты Excel roundtrip (план/факт KPI и парсинг)."""

import math
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.client_bot.user_interface.services.adv_excel_roundtrip.deviation import (
    compute_deviation_metrics,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EXCEL_TEMPLATE_VERSION,
    column_header,
    edit_header,
    enum_names_for_field,
    header_type_suffix,
    parse_edit_value,
    parse_header,
    serialize_shelf_bid_control_cell,
)
from app.client_bot.user_interface.handlers.adv_excel_roundtrip import _ProgressReporter
from app.client_bot.user_interface.services.adv_excel_roundtrip.export_build import (
    _first_offer_id_from_nmid,
)


@pytest.mark.unit
def test_deviation_score_euclidean() -> None:
    # plan 10 orders, fact 5 -> -50%; target cost 100, fact 200 -> +100%
    d = compute_deviation_metrics(
        fact_orders_per_day=5.0,
        plan_orders_per_day=10,
        fact_cost_per_order=200.0,
        target_cost_per_order=100.0,
    )
    assert d.orders_dev_pct == pytest.approx(-50.0)
    assert d.cost_dev_pct == pytest.approx(100.0)
    assert d.deviation_score == pytest.approx(math.sqrt(50.0**2 + 100.0**2))


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
def test_edit_header_aggressiveness_uses_orm_field_name() -> None:
    h = edit_header("aggressiveness")
    k, f, s = parse_header(h)
    assert k == "EDIT"
    assert f == "aggressiveness"
    assert s == "INT"


@pytest.mark.unit
def test_edit_header_keyword_calibration_step_uses_orm_field_name() -> None:
    h = edit_header("keyword_calibration_max_step")
    k, f, s = parse_header(h)
    assert k == "EDIT"
    assert f == "keyword_calibration_max_step"
    assert s == "INT"


@pytest.mark.unit
def test_parse_header_edit_bool() -> None:
    k, f, s = parse_header("EDIT__bot_active__BOOL")
    assert k == "EDIT"
    assert f == "bot_active"
    assert s == "BOOL"


@pytest.mark.unit
def test_parse_header_with_russian_label_and_tech_key() -> None:
    h = "Стратегия (EDIT__strategy__ENUM)"
    k, f, s = parse_header(h)
    assert k == "EDIT"
    assert f == "strategy"
    assert s == "ENUM"


@pytest.mark.unit
def test_column_header_contains_tech_key() -> None:
    h = column_header("RO", "adv_id")
    assert "ID единой ставки" in h
    assert "(RO__adv_id)" in h


@pytest.mark.unit
def test_column_header_auto_common_budget_label() -> None:
    h = column_header("EDIT", "auto_common_budget", "BOOL")
    assert "Авторасчёт общего бюджета" in h
    assert "(EDIT__auto_common_budget__BOOL)" in h


@pytest.mark.unit
def test_parse_header_backward_compatible_with_old_template() -> None:
    k, f, s = parse_header("RO__adv_setting_id")
    assert k == "RO"
    assert f == "adv_setting_id"
    assert s == ""


@pytest.mark.unit
def test_parse_edit_bool_from_excel() -> None:
    assert parse_edit_value("bot_active", True) is True
    assert parse_edit_value("bot_active", "FALSE") is False


@pytest.mark.unit
def test_parse_edit_enum_accepts_enum_name() -> None:
    v = parse_edit_value("strategy", "MIN_CPO")
    assert str(v.name) == "MIN_CPO"


@pytest.mark.unit
def test_enum_names_for_field_strategy() -> None:
    values = enum_names_for_field("strategy")
    assert "MIN_CPO" in values
    assert "MAX_CONV" in values


@pytest.mark.unit
def test_parse_edit_bool_v3_raise_max_cpo() -> None:
    assert parse_edit_value("substitute_fact_cpo_for_max", "TRUE") is True
    assert parse_edit_value("substitute_fact_cpo_for_max", "FALSE") is False
    assert header_type_suffix("substitute_fact_cpo_for_max") == "BOOL"


@pytest.mark.unit
def test_template_version_constant() -> None:
    assert EXCEL_TEMPLATE_VERSION == 7


@pytest.mark.unit
def test_edit_header_auto_shelf_max_bid_uses_technical_field_name() -> None:
    h = edit_header("auto_shelf_max_bid_rub")
    k, f, s = parse_header(h)
    assert k == "EDIT"
    assert f == "auto_shelf_max_bid_rub"
    assert s == "INT"


@pytest.mark.unit
def test_parse_edit_shelf_max_bid_to_minor_units() -> None:
    assert parse_edit_value("auto_shelf_max_bid_rub", 600) == 60_000
    assert parse_edit_value("auto_shelf_min_bid_distance_rub", "1") == 100


@pytest.mark.unit
def test_parse_edit_shelf_test_share_accepts_percent_input() -> None:
    assert parse_edit_value("auto_shelf_test_share", "10") == pytest.approx(0.1)
    assert parse_edit_value("auto_shelf_test_share", 0.1) == pytest.approx(0.1)


@pytest.mark.unit
def test_serialize_edit_shelf_values_converts_minor_units_to_rubles() -> None:
    assert serialize_shelf_bid_control_cell("auto_shelf_max_bid_rub", 60_000) == 600.0
    assert serialize_shelf_bid_control_cell("auto_shelf_min_bid_distance_rub", 100) == 1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_progress_reporter_throttles_messages() -> None:
    bot = AsyncMock()
    reporter = _ProgressReporter(bot=bot, chat_id=1, title="Импорт Excel", min_step=10)
    await reporter.start()
    await reporter.tick(1, 100)
    await reporter.tick(5, 100)
    await reporter.tick(10, 100)
    await reporter.tick(20, 100)

    # start + 10% + 20%
    assert bot.send_message.await_count == 3


@pytest.mark.unit
def test_first_offer_id_by_nmid_returns_value() -> None:
    adv = SimpleNamespace(id=7)
    assert (
        _first_offer_id_from_nmid(adv, first_nmid=123, offer_by_nmid={123: "ABC-123"})
        == "ABC-123"
    )


@pytest.mark.unit
def test_first_offer_id_by_nmid_raises_when_missing() -> None:
    adv = SimpleNamespace(id=7)
    with pytest.raises(ValueError):
        _first_offer_id_from_nmid(adv, first_nmid=123, offer_by_nmid={})
