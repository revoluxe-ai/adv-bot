from typing import Awaitable, Callable

from app.core.mp.wb.api.adapter.promotion_client.minus_phrases.post_adv_v0_normquery_set_minus import (
    SetMinusPhrasesCommand,
)


async def request(
    method: Callable[[SetMinusPhrasesCommand], Awaitable[None]],
    command: SetMinusPhrasesCommand,
) -> None:
    command = SetMinusPhrasesCommand(
        advert_id=command.advert_id,
        nm_id=command.nm_id,
        norm_queries=command.norm_queries,
    )
    await method(command)
    return None
