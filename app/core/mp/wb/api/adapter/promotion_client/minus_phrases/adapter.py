import logging

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.api.campaign_parameters \
    import post_adv_v0_normquery_set_minus
from ..base_section_adapter import BaseSectionAdapter
from app.core.mp.wb.api.retry_decorator import retry_decorator
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors

from .post_adv_v0_normquery_set_minus import (
    SetMinusPhrasesCommand,
    command_to_body,

)

logger = logging.getLogger(__name__)


class MinusPhrasesAdapter(BaseSectionAdapter):
    @retry_decorator(period=1, limit=5)  # 5 req/sec
    async def post_adv_v0_normquery_set_minus(
        self, command: SetMinusPhrasesCommand
    ) -> None:
        body = command_to_body.convert(command)
        client = await self.auth_client_handler.get_proxy_client(self)
        try:
            response = await with_raise_errors(post_adv_v0_normquery_set_minus.asyncio_detailed,
                                           client,
                                           body=body)
        except Exception as exc:
            logger.error('Ошибка обновления минус-фраз', exc_info=True)
            raise exc
        logger.debug(response)
        return None
