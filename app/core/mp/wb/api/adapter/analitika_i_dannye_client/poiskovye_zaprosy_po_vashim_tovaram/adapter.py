from typing import Any, cast
from app.core.mp.wb.api.generated.analitika_i_dannye_client.types import Response
from ..base_section_adapter import BaseSectionAdapter
from app.core.mp.wb.api.retry_decorator import retry_decorator
from app.core.mp.wb.dto import KeywordPosition
from .post_api_v2_search_report_product_orders import (
    GetKeywordPositionsCommand,
    command_to_body,
    raw_response_to_dto,
    with_raise_errors,
    asyncio_detailed,
)


class Adapter(BaseSectionAdapter):

    @retry_decorator(60, 3)
    async def post_api_v2_search_report_product_orders(
        self,
        command: GetKeywordPositionsCommand,
    ) -> list[KeywordPosition]:
        body = command_to_body(command)
        client = await self.auth_client_handler.get_proxy_client(self)
        raw_response = await with_raise_errors(asyncio_detailed, client, body)
        raw_response = cast(Response[Any], raw_response)
        dto: list[KeywordPosition] = raw_response_to_dto(command.nmid, raw_response)
        return dto
