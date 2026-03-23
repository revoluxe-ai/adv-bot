from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    V0GetNormQueryMinusRequest,
    V0GetNormQueryMinusRequestItem,
)

from .command import GetMinusPhrasesCommand


def convert(command: GetMinusPhrasesCommand) -> V0GetNormQueryMinusRequest:
    item = V0GetNormQueryMinusRequestItem(
        advert_id=command.advert_id,
        nm_id=command.nm_id,
    )
    return V0GetNormQueryMinusRequest(items=[item])
