from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
    GetNormqueryStatsCommand,
)

from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.models import (
    V0GetNormQueryStatsRequest,
    V0GetNormQueryStatsRequestItemsItem,
)

def command_to_body(command: GetNormqueryStatsCommand) -> V0GetNormQueryStatsRequest:
    items: list[V0GetNormQueryStatsRequestItemsItem] = []

    for complex_adv in command.complex_advs:
        item = V0GetNormQueryStatsRequestItemsItem(
        advert_id=complex_adv.adv_id,
        nm_id=complex_adv.main_nmid)
        items.append(item)

    body = V0GetNormQueryStatsRequest(
        from_=command.date_from,
        to=command.date_to,
        items=items,
    )
    return body
