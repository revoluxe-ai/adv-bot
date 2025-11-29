from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
    GetNormqueryStatsCommand,
)

from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.models import (
    V0GetNormQueryStatsRequest,
    V0GetNormQueryStatsRequestItemsItem,
)

def command_to_body(command: GetNormqueryStatsCommand) -> V0GetNormQueryStatsRequest:
    items_item = V0GetNormQueryStatsRequestItemsItem(
        advert_id=command.advert_id,
        nm_id=command.nmid,
    )
    request = V0GetNormQueryStatsRequest(
        from_=command.date_from,
        to=command.date_to,
        items=[items_item],
    )
    return request
