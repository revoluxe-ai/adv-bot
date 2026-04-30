import logging
from typing import cast

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.api.campaign_parameters import (
    post_adv_v0_normquery_set_minus,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.api.search_clusters import (
    post_adv_v0_normquery_get_minus,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    V0GetNormQueryMinusResponse,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.types import UNSET
from ..base_section_adapter import BaseSectionAdapter
from app.core.mp.wb.api.retry_decorator import retry_decorator
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.excs import BadRequestError

from .get_adv_v0_normquery_get_minus import GetMinusPhrasesCommand
from .get_adv_v0_normquery_get_minus import command_to_body as get_minus_command_to_body
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
        except BadRequestError:
            # Это ожидаемый сценарий для fallback: верхний слой может
            # перехватить ошибку, удалить невалидную фразу и успешно повторить.
            logger.debug("WB отклонил часть минус-фраз (recoverable для fallback)")
            raise
        except Exception as exc:
            logger.error('Ошибка обновления минус-фраз', exc_info=True)
            raise exc
        logger.debug(response)
        return None

    @retry_decorator(period=1, limit=5)  # 5 req/sec
    async def post_adv_v0_normquery_get_minus(
        self, command: GetMinusPhrasesCommand
    ) -> list[str]:
        body = get_minus_command_to_body.convert(command)
        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(
            post_adv_v0_normquery_get_minus.asyncio_detailed,
            client,
            body=body,
        )
        parsed = response.parsed
        if not isinstance(parsed, V0GetNormQueryMinusResponse) or not parsed.items:
            return []
        item = parsed.items[0]
        if item.norm_queries is UNSET:
            return []
        norm_queries = cast(list[str], item.norm_queries)
        return list(norm_queries)
