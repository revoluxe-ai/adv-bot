from app.core.mp.wb.api.generated.analitika_i_dannye_client.models import ProductOrdersRequest, PeriodOrdersRequest
from .command import GetKeywordPositionsCommand



def convert(command: GetKeywordPositionsCommand) -> ProductOrdersRequest:
    period = PeriodOrdersRequest(
        start=command.start,
        end=command.end,
    )

    body = ProductOrdersRequest(
        search_texts=command.texts,
        nm_id=command.nmid,
        period=period,
    )
    return body

