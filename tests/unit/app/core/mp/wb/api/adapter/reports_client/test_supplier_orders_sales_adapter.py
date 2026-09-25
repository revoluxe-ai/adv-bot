"""Unit: SupplierOrdersSalesAdapter — mock generated client, no invent URL."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

from app.core.mp.wb.api.adapter.reports_client.adapter import SupplierOrdersSalesAdapter
from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum
from app.core.mp.wb.api.generated.reports.v1.reports_client.models.orders_item import (
    OrdersItem,
)


@pytest.mark.asyncio
async def test_adapter_get_supplier_orders_uses_generated_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adapter принимает mock HTTP/client response; URL только из generated module."""
    from app.core.mp.wb.api.generated.reports.v1.reports_client.api.main_reports import (
        get_api_v1_supplier_orders,
    )

    assert "/api/v1/supplier/orders" in get_api_v1_supplier_orders.__file__.replace(
        "\\", "/"
    ) or hasattr(get_api_v1_supplier_orders, "asyncio_detailed")

    order = OrdersItem()
    order.srid = "srid-1"
    order.last_change_date = "2026-07-04T10:00:00"

    captured: dict[str, Any] = {}

    async def _fake_detailed(*, client: object, date_from: str, flag: object) -> Any:
        captured["date_from"] = date_from
        captured["flag"] = flag
        captured["client"] = client
        return SimpleNamespace(parsed=[order], status_code=200)

    monkeypatch.setattr(
        get_api_v1_supplier_orders,
        "asyncio_detailed",
        _fake_detailed,
    )

    auth = MagicMock()
    proxy = MagicMock()
    auth.get_proxy_client = AsyncMock(return_value=proxy)
    auth.shop_id = "shop-1"
    limit_mgr = MagicMock()
    limit_mgr.api_call_state = {}

    adapter = SupplierOrdersSalesAdapter(
        base_url="https://statistics-api.wildberries.ru",
        auth_client_handler=auth,
        request_limit_manager=limit_mgr,
    )
    assert adapter.section is SectionsEnum.STATISTICS

    async def _passthrough(fn: Any, client: object, **kwargs: Any) -> Any:
        return await fn(client=client, **kwargs)

    monkeypatch.setattr(
        "app.core.mp.wb.api.adapter.reports_client.adapter.with_raise_errors",
        _passthrough,
    )

    rows = await adapter.get_supplier_orders(date_from="2026-07-04", flag=0)
    assert len(rows) == 1
    assert rows[0].srid == "srid-1"
    assert captured["date_from"] == "2026-07-04"
    assert captured["client"] is proxy
