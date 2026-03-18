from app.core.mp.wb.api.adapter.promotion_client.minus_phrases.adapter import (
    MinusPhrasesAdapter,
)
from app.core.mp.wb.api.adapter.promotion_client.minus_phrases.get_adv_v0_normquery_get_minus import (
    GetMinusPhrasesCommand,
)


async def get_minus_phrases(
    minus_phrases_adapter: MinusPhrasesAdapter,
    advert_id: int,
    nm_id: int,
) -> list[str]:
    command = GetMinusPhrasesCommand(advert_id=advert_id, nm_id=nm_id)
    return await minus_phrases_adapter.post_adv_v0_normquery_get_minus(command)
