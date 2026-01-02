from typing import cast

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.generated.analitika_i_dannye_client.models import (
    ProductHistoryResponseItem,
)
from app.core.mp.wb.api.generated.analitika_i_dannye_client.types import Response
from app.core.mp.wb.api.retry_decorator import retry_decorator

from .post_sales_funnel_products_history import (
    CommonSaleStatRow,
    SalesFunnelProductsHistoryCommand,
    asyncio_detailed,
    command_to_body,
    raw_response_to_dto,
    with_raise_errors,
)


class Adapter(BaseSectionAdapter):
    @retry_decorator(60, 3)
    async def post_sales_funnel_products_history(
        self,
        command: SalesFunnelProductsHistoryCommand,
    ) -> list[CommonSaleStatRow]:
        body = command_to_body(command)
        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(asyncio_detailed, client, body)
        response = cast(Response[list[ProductHistoryResponseItem]], response)
        parsed = response.parsed
        if parsed is None:
            return []
        dto = raw_response_to_dto(parsed)
        return dto


