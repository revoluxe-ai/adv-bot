from __future__ import annotations

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    V0GetNormQueryBidsRequest,
    V0GetNormQueryBidsRequestItem,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)


def dto_to_request(complex_advs: list[ComplexAdv]) -> V0GetNormQueryBidsRequest:
    """Собирает тело запроса normquery/get-bids для переданных рекламных кампаний.

    Normquery cluster bids живут только в search (auction) РК — запрашиваем
    ``search_adv_id``, не auto ``adv_id``.
    """

    items: list[V0GetNormQueryBidsRequestItem] = []
    for adv in complex_advs:
        nmids = adv.nmids
        if not nmids:
            continue

        search_adv_id = adv.search_adv_id
        if search_adv_id is None and (search_adv := adv.search_adv) is not None:
            search_adv_id = search_adv.adv_id
        if search_adv_id is None:
            continue
        items.extend(_build_items(search_adv_id, nmids))

    return V0GetNormQueryBidsRequest(items=items)


def _build_items(
    advert_id: int, nmids: list[int]
) -> list[V0GetNormQueryBidsRequestItem]:
    return [
        V0GetNormQueryBidsRequestItem(advert_id=advert_id, nm_id=nmid)
        for nmid in nmids
    ]
