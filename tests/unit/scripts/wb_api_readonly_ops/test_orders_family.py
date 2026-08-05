"""Unit: ORDERS_OR_SALES_REPORTS_READ — Stage A orders+sales (INC-RO-07).

Spec delta: wb-api-read-only-preflight (Stage A requests orders and sales;
period attestation; family status when sales fails; anti-substitution).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

from scripts.wb_api_readonly_ops.ceiling import RunCeiling
from scripts.wb_api_readonly_ops.families import HubFamilyRunners
from scripts.wb_api_readonly_ops.models import (
    FAMILY_ORDER,
    ORDERS_PERIOD_DATE_FROM_DEFAULT,
    FamilyName,
    FamilyResult,
    FamilyStatus,
    Mode,
)
from scripts.wb_api_readonly_ops.orchestrator import run_ops


def _dm_with_reports(
    *,
    orders: object | BaseException | None = None,
    sales: object | BaseException | None = None,
) -> MagicMock:
    """Собрать wb_data_manager mock с reports_manager orders/sales.

    Args:
        orders/sales: return_value list, или Exception для side_effect fail.
    """
    reports_manager = MagicMock()
    if isinstance(orders, BaseException):
        reports_manager.get_supplier_orders = AsyncMock(side_effect=orders)
    else:
        reports_manager.get_supplier_orders = AsyncMock(
            return_value=[] if orders is None else orders
        )
    if isinstance(sales, BaseException):
        reports_manager.get_supplier_sales = AsyncMock(side_effect=sales)
    else:
        reports_manager.get_supplier_sales = AsyncMock(
            return_value=[] if sales is None else sales
        )
    dm = MagicMock()
    dm.reports_manager = reports_manager
    dm.get_sales_funnel_products_history = AsyncMock(
        return_value=[{"orders": 99}]
    )
    dm.promotion_manager = MagicMock()
    dm.promotion_manager.get_full_adv_stat = AsyncMock(
        return_value=[{"orders": 42}]
    )
    return dm


@pytest.mark.asyncio
async def test_orders_family_runs_first_in_orchestrator() -> None:
    """ORDERS_OR_SALES_REPORTS_READ выполняется первой (FAMILY_ORDER).

    Docstring/requirement: ORDERS_OR_SALES_REPORTS_READ family.
    """
    assert FAMILY_ORDER[0] is FamilyName.ORDERS_OR_SALES_REPORTS_READ
    seen: list[str] = []

    def _make(name: FamilyName):
        async def _runner(mode: Mode, ctx: dict[str, Any]) -> FamilyResult:
            seen.append(name.value)
            return FamilyResult(family=name, status=FamilyStatus.OK)

        return _runner

    runners = {f: _make(f) for f in FAMILY_ORDER}
    report = await run_ops(
        shop_id="s1",
        mode=Mode.PREFLIGHT,
        runners=runners,
        ceiling=RunCeiling(max_seconds=60, max_calls=20),
    )
    assert seen[0] == FamilyName.ORDERS_OR_SALES_REPORTS_READ.value
    assert report.families[0].family is FamilyName.ORDERS_OR_SALES_REPORTS_READ


@pytest.mark.asyncio
async def test_stage_a_calls_orders_and_sales_same_date_from() -> None:
    """Stage A MUST вызвать get_supplier_orders и get_supplier_sales (один dateFrom).

    Spec: Stage A requests orders and sales; ORDERS period attestation.
    Characterization до INC-RO-07: вызывался только orders — теперь оба.
    """
    dm = _dm_with_reports(
        orders=[{"srid": "ord-1"}],
        sales=[{"saleID": "sale-1"}],
    )
    result = await HubFamilyRunners(dm).run_orders_or_sales_reports_read(
        Mode.PREFLIGHT,
        {"orders_date_from": ORDERS_PERIOD_DATE_FROM_DEFAULT.isoformat()},
    )
    rm = dm.reports_manager
    rm.get_supplier_orders.assert_called_once()
    rm.get_supplier_sales.assert_called_once()
    assert rm.get_supplier_orders.await_args.kwargs["date_from"] == "2026-07-04"
    assert rm.get_supplier_sales.await_args.kwargs["date_from"] == "2026-07-04"
    assert result.payload is not None
    assert result.payload["next_page_followed"] == "NO"
    assert result.payload["period_parameter_model"] == "DATE_FROM_CURSOR"
    assert result.payload["orders"]["rows_count"] == 1
    assert result.payload["sales"]["rows_count"] == 1
    assert result.status is FamilyStatus.OK


@pytest.mark.asyncio
async def test_orders_ok_sales_fail_yields_partial() -> None:
    """Orders OK + sales fail → PARTIAL + sales gap + orders retained.

    Spec: Stage A family status when sales fails after orders.
    """
    dm = _dm_with_reports(
        orders=[{"srid": "ord-1"}],
        sales=RuntimeError("sales down"),
    )
    result = await HubFamilyRunners(dm).run_orders_or_sales_reports_read(
        Mode.PREFLIGHT, {}
    )
    assert result.status is FamilyStatus.PARTIAL
    assert any("sales" in g for g in result.gaps)
    assert result.payload is not None
    assert result.payload["orders"]["rows_count"] == 1
    assert result.payload["sales"]["rows_count"] == 0


@pytest.mark.asyncio
async def test_orders_fail_is_family_failed() -> None:
    """Orders fail → FAILED / non-success + orders gap.

    Spec: Stage A family status when sales fails after orders (orders failure).
    """
    dm = _dm_with_reports(
        orders=RuntimeError("orders down"),
        sales=[{"saleID": "sale-1"}],
    )
    result = await HubFamilyRunners(dm).run_orders_or_sales_reports_read(
        Mode.PREFLIGHT, {}
    )
    assert result.status is FamilyStatus.FAILED
    assert any("orders" in g for g in result.gaps)
    dm.reports_manager.get_supplier_sales.assert_not_called()


@pytest.mark.asyncio
async def test_empty_orders_and_sales_pages_are_partial() -> None:
    """Пустые first pages → PARTIAL + gaps, не silent OK.

    Spec: Targeted automated coverage / empty page honesty (INC-RO-07).
    """
    dm = _dm_with_reports(orders=[], sales=[])
    result = await HubFamilyRunners(dm).run_orders_or_sales_reports_read(
        Mode.PREFLIGHT, {}
    )
    assert result.status is FamilyStatus.PARTIAL
    assert any("orders" in g for g in result.gaps)
    assert any("sales" in g for g in result.gaps)


@pytest.mark.asyncio
async def test_anti_substitution_funnel_not_counted_as_orders() -> None:
    """Успех funnel не засчитывается как OK для ORDERS; guard: funnel не вызывается.

    Paired: статус берётся из get_supplier_orders/sales, не funnel/fullstats.
    """
    dm = _dm_with_reports(
        orders=[{"srid": "ord-1", "lastChangeDate": "2026-07-04T12:00:00"}],
        sales=[{"saleID": "s1"}],
    )
    result = await HubFamilyRunners(dm).run_orders_or_sales_reports_read(
        Mode.PREFLIGHT,
        {"orders_date_from": ORDERS_PERIOD_DATE_FROM_DEFAULT.isoformat()},
    )

    dm.get_sales_funnel_products_history.assert_not_called()
    dm.promotion_manager.get_full_adv_stat.assert_not_called()
    dm.reports_manager.get_supplier_orders.assert_called_once()
    dm.reports_manager.get_supplier_sales.assert_called_once()
    assert result.family is FamilyName.ORDERS_OR_SALES_REPORTS_READ
    assert result.status is FamilyStatus.OK
    assert result.payload is not None
    assert "funnel" not in str(result.payload).lower()
    assert result.payload["orders"]["source"] == "statistics-api.supplier.orders"
    assert result.payload["sales"]["source"] == "statistics-api.supplier.sales"


@pytest.mark.asyncio
async def test_orders_period_stage_a_uses_contract_date_from_no_next_page() -> None:
    """Stage A: dateFrom=2026-07-04 (Moscow); без yesterday→today; next_page=NO."""
    dm = _dm_with_reports(orders=[], sales=[])
    result = await HubFamilyRunners(dm).run_orders_or_sales_reports_read(
        Mode.PREFLIGHT,
        {},
    )

    call_kwargs = dm.reports_manager.get_supplier_orders.await_args.kwargs
    sales_kwargs = dm.reports_manager.get_supplier_sales.await_args.kwargs
    assert call_kwargs["date_from"] == "2026-07-04"
    assert sales_kwargs["date_from"] == "2026-07-04"
    assert ORDERS_PERIOD_DATE_FROM_DEFAULT.isoformat() == "2026-07-04"
    assert result.payload is not None
    assert result.payload["date_from"] == "2026-07-04"
    assert result.payload["next_page_followed"] == "NO"
    assert result.payload["period_parameter_model"] == "DATE_FROM_CURSOR"
    assert result.status is FamilyStatus.PARTIAL


@pytest.mark.asyncio
async def test_anti_substitution_guard_fails_if_orders_runner_uses_funnel() -> None:
    """Regression: если ORDERS runner ошибочно зовёт funnel — тест падает.

    Симулирует forbidden substitution path и проверяет, что production runner
    не идёт этим путём (paired negative относительно guard).
    """
    dm = _dm_with_reports(orders=[], sales=[])
    dm.get_sales_funnel_products_history = AsyncMock(return_value=[{"ok": True}])

    async def _forbidden_orders_via_funnel(
        mode: Mode, ctx: dict[str, Any]
    ) -> FamilyResult:
        rows = await dm.get_sales_funnel_products_history(
            nmids=[1], start=None, end=None
        )
        return FamilyResult(
            family=FamilyName.ORDERS_OR_SALES_REPORTS_READ,
            status=FamilyStatus.OK if rows else FamilyStatus.FAILED,
            payload={"source": "funnel"},
        )

    forbidden = await _forbidden_orders_via_funnel(Mode.PREFLIGHT, {})
    assert forbidden.payload["source"] == "funnel"
    dm.get_sales_funnel_products_history.assert_called()

    dm.get_sales_funnel_products_history.reset_mock()
    real = await HubFamilyRunners(dm).run_orders_or_sales_reports_read(
        Mode.PREFLIGHT, {}
    )
    dm.get_sales_funnel_products_history.assert_not_called()
    assert real.payload is not None
    assert real.payload.get("source") != "funnel"
    assert real.payload["orders"]["source"] == "statistics-api.supplier.orders"
    assert real.payload["sales"]["source"] == "statistics-api.supplier.sales"
