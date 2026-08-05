"""Адаптер GET supplier orders/sales на statistics-api (узкий surface INC-RO-06).

Identity: ORDERS_OR_SALES_REPORTS_READ — только statistics-api GET
`/api/v1/supplier/orders` и `/api/v1/supplier/sales` через generated Reports
client. Не подменять funnel / fullstats / FBS (decision
orders-or-sales-reports-read-identity).
"""

from __future__ import annotations

from typing import Any, Union, cast

from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.adapter.reports_client.base_section_adapter import (
    BaseStatisticsSectionAdapter,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator
from app.core.mp.wb.api.generated.reports.v1.reports_client.api.main_reports import (
    get_api_v1_supplier_orders,
    get_api_v1_supplier_sales,
)
from app.core.mp.wb.api.generated.reports.v1.reports_client.models.orders_item import (
    OrdersItem,
)
from app.core.mp.wb.api.generated.reports.v1.reports_client.models.sales_item import (
    SalesItem,
)
from app.core.mp.wb.api.generated.reports.v1.reports_client.types import UNSET, Unset


class SupplierOrdersSalesAdapter(BaseStatisticsSectionAdapter):
    """Узкий фасад Reports: только GET supplier orders и sales."""

    @retry_decorator(period=60, limit=3)
    async def get_supplier_orders(
        self,
        *,
        date_from: str,
        flag: int | None = 0,
    ) -> list[OrdersItem]:
        """GET /api/v1/supplier/orders (statistics-api).

        Args:
            date_from: RFC3339 / дата в Москве (контракт API `dateFrom`).
            flag: query `flag` (0 = изменения с dateFrom; см. swagger).

        Returns:
            Список OrdersItem одной страницы ответа (Stage A: без follow cursor).
        """
        client = await self.auth_client_handler.get_proxy_client(self)
        flag_param: Union[Unset, int] = UNSET if flag is None else flag
        response = await with_raise_errors(
            get_api_v1_supplier_orders.asyncio_detailed,
            client,
            date_from=date_from,
            flag=flag_param,
        )
        if response is None or response.parsed is None:
            return []
        parsed: Any = response.parsed
        if isinstance(parsed, list):
            return cast(list[OrdersItem], parsed)
        return []

    @retry_decorator(period=60, limit=3)
    async def get_supplier_sales(
        self,
        *,
        date_from: str,
        flag: int | None = 0,
    ) -> list[SalesItem]:
        """GET /api/v1/supplier/sales (statistics-api).

        Args:
            date_from: RFC3339 / дата в Москве (`dateFrom`).
            flag: query `flag`.

        Returns:
            Список SalesItem одной страницы ответа.
        """
        client = await self.auth_client_handler.get_proxy_client(self)
        flag_param: Union[Unset, int] = UNSET if flag is None else flag
        response = await with_raise_errors(
            get_api_v1_supplier_sales.asyncio_detailed,
            client,
            date_from=date_from,
            flag=flag_param,
        )
        if response is None or response.parsed is None:
            return []
        parsed: Any = response.parsed
        if isinstance(parsed, list):
            return cast(list[SalesItem], parsed)
        return []
