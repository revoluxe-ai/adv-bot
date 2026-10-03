"""Доменный менеджер Reports: только supplier orders/sales GET (INC-RO-06)."""

from __future__ import annotations

from app.core.mp.wb.api.adapter.reports_client import SupplierOrdersSalesAdapter
from app.core.mp.wb.api.generated.reports.v1.reports_client.models.orders_item import (
    OrdersItem,
)
from app.core.mp.wb.api.generated.reports.v1.reports_client.models.sales_item import (
    SalesItem,
)


class ReportsManager:
    """Тонкий фасад над SupplierOrdersSalesAdapter для hub / readonly_ops.

    Не экспонирует finance и прочие Reports ops — только orders/sales GET.
    """

    def __init__(self, supplier_orders_sales_adapter: SupplierOrdersSalesAdapter) -> None:
        self._adapter = supplier_orders_sales_adapter

    async def get_supplier_orders(
        self,
        *,
        date_from: str,
        flag: int | None = 0,
    ) -> list[OrdersItem]:
        """Получить ленту заказов поставщика (statistics-api GET)."""
        return await self._adapter.get_supplier_orders(
            date_from=date_from,
            flag=flag,
        )

    async def get_supplier_sales(
        self,
        *,
        date_from: str,
        flag: int | None = 0,
    ) -> list[SalesItem]:
        """Получить ленту продаж/возвратов поставщика (statistics-api GET)."""
        return await self._adapter.get_supplier_sales(
            date_from=date_from,
            flag=flag,
        )
