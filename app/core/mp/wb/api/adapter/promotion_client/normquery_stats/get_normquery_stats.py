from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
    GetNormqueryStatsCommand,
)

from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.models import (
    V0GetNormQueryStatsRequest,
    V0GetNormQueryStatsRequestItemsItem,
)

def command_to_bodies(command: GetNormqueryStatsCommand) -> list[V0GetNormQueryStatsRequest]:
    #TODO: тут поймали бесконечный цикл, забыл с
    len_batch = 100
    offset = 0
    adv_batchs = command.batchs
    bodies: list[V0GetNormQueryStatsRequest] = []
    while offset < len(adv_batchs):
        current_batch = adv_batchs[offset:offset + len_batch]
        items: list[V0GetNormQueryStatsRequestItemsItem] = []
        for adv_batch in current_batch:
            item =  V0GetNormQueryStatsRequestItemsItem(
                advert_id=adv_batch.adv_id,
                nm_id=adv_batch.nmid,
            )
            items.append(item)
        body = V0GetNormQueryStatsRequest(
            from_=command.date_from,
            to=command.date_to,
            items=items,
        )
        bodies.append(body)
        offset += len_batch

    return bodies
