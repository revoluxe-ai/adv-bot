from .command import SalesFunnelProductsHistoryCommand
from .command_to_body import convert as command_to_body
from .dto import CommonSaleStatRow
from .raw_response_to_dto import convert as raw_response_to_dto
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.analitika_i_dannye_client.api.voronka_prodazh.post_sales_funnel_products_history import (
    asyncio_detailed,
)

__all__ = [
    "SalesFunnelProductsHistoryCommand",
    "command_to_body",
    "CommonSaleStatRow",
    "raw_response_to_dto",
    "with_raise_errors",
    "asyncio_detailed",
]


