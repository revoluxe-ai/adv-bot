import datetime
from typing import Awaitable

from typing import Callable

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.\
    poiskovye_zaprosy_po_vashim_tovaram.post_api_v2_search_report_product_orders import \
    GetKeywordPositionsCommand
from app.core.mp.wb.dto import KeywordPosition



async def request(
    method: Callable[[GetKeywordPositionsCommand], Awaitable[list[KeywordPosition]]],
    nmid: int,
    texts: list[str],
    for_last_days: int
) -> list[KeywordPosition]:
    """Обычный тариф - макс 30 ключей за раз, продвинутый - 100"""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    from_date = today - datetime.timedelta(days=for_last_days - 1)
    result: list[KeywordPosition] = []
    batch_len = 30
    offset = 0
    while offset < len(texts):
        current_batch = texts[offset:offset + batch_len]

        command = GetKeywordPositionsCommand(
            nmid=nmid,
            start=from_date,
            end=today,
            texts=current_batch
        )

        response = await method(command)
        result.extend(response)
        offset += batch_len

    return result
