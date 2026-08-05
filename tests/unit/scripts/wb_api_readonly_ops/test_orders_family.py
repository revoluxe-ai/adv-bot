"""Unit: ORDERS_OR_SALES_REPORTS_READ family — order, period, anti-substitution.

Requirement: ORDERS_OR_SALES_REPORTS_READ family (delta
wb-api-read-only-preflight); INC-RO-06 Stage A period attestation.
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
async def test_anti_substitution_funnel_not_counted_as_orders() -> None:
    """Успех funnel не засчитывается как OK для ORDERS; guard: funnel не вызывается.

    Paired: при реальном ORDERS runner статус берётся из get_supplier_orders.
    """
    reports_manager = MagicMock()
    reports_manager.get_supplier_orders = AsyncMock(
        return_value=[{"srid": "ord-1", "lastChangeDate": "2026-07-04T12:00:00"}]
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

    runners = HubFamilyRunners(dm)
    result = await runners.run_orders_or_sales_reports_read(
        Mode.PREFLIGHT,
        {"orders_date_from": ORDERS_PERIOD_DATE_FROM_DEFAULT.isoformat()},
    )

    dm.get_sales_funnel_products_history.assert_not_called()
    dm.promotion_manager.get_full_adv_stat.assert_not_called()
    reports_manager.get_supplier_orders.assert_called_once()
    assert result.family is FamilyName.ORDERS_OR_SALES_REPORTS_READ
    assert result.status is FamilyStatus.OK
    assert result.payload is not None
    assert result.payload.get("source") == "statistics-api.supplier.orders"
    assert "funnel" not in str(result.payload).lower()


@pytest.mark.asyncio
async def test_orders_period_stage_a_uses_contract_date_from_no_next_page() -> None:
    """Stage A: dateFrom=2026-07-04 (Moscow); без yesterday→today; next_page=NO."""
    reports_manager = MagicMock()
    reports_manager.get_supplier_orders = AsyncMock(return_value=[])
    dm = MagicMock()
    dm.reports_manager = reports_manager

    runners = HubFamilyRunners(dm)
    result = await runners.run_orders_or_sales_reports_read(
        Mode.PREFLIGHT,
        {},
    )

    call_kwargs = reports_manager.get_supplier_orders.await_args.kwargs
    assert call_kwargs["date_from"] == "2026-07-04"
    assert ORDERS_PERIOD_DATE_FROM_DEFAULT.isoformat() == "2026-07-04"
    assert result.payload is not None
    assert result.payload["date_from"] == "2026-07-04"
    assert result.payload["next_page_followed"] == "NO"
    assert result.payload["period_parameter_model"] == "DATE_FROM_CURSOR"
    assert result.status in (FamilyStatus.OK, FamilyStatus.PARTIAL)


@pytest.mark.asyncio
async def test_anti_substitution_guard_fails_if_orders_runner_uses_funnel() -> None:
    """Regression: если ORDERS runner ошибочно зовёт funnel — тест падает.

    Симулирует forbidden substitution path и проверяет, что production runner
    не идёт этим путём (paired negative относительно guard).
    """
    reports_manager = MagicMock()
    reports_manager.get_supplier_orders = AsyncMock(return_value=[])
    dm = MagicMock()
    dm.reports_manager = reports_manager
    dm.get_sales_funnel_products_history = AsyncMock(return_value=[{"ok": True}])

    # Forbidden alternate: mark ORDERS OK from funnel — must NOT be what Hub uses.
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
    assert real.payload.get("source") == "statistics-api.supplier.orders"
