from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    V0SetMinusNormQueryRequest,
)
from .command import SetMinusPhrasesCommand

def convert(command: SetMinusPhrasesCommand) -> V0SetMinusNormQueryRequest:
    body = V0SetMinusNormQueryRequest(
        advert_id=command.advert_id,
        nm_id=command.nm_id,
        norm_queries=command.norm_queries,
    )
    return body
