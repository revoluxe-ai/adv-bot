from __future__ import annotations

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    V0GetNormQueryBidsRequest,
    V0GetNormQueryBidsRequestItem,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)


def dto_to_request(complex_advs: list[ComplexAdv]) -> V0GetNormQueryBidsRequest:
    """Собирает тело запроса normquery/get-bids для переданных рекламных кампаний."""

    items: list[V0GetNormQueryBidsRequestItem] = []
    for adv in complex_advs:
        nmids = adv.nmids
        if not nmids:
            continue

        items.extend(_build_items(adv.auto_adv_id, nmids))
        if search_adv := adv.search_adv:
            items.extend(_build_items(search_adv.adv_id, nmids))

    return V0GetNormQueryBidsRequest(items=items)


def _build_items(
    advert_id: int, nmids: list[int]
) -> list[V0GetNormQueryBidsRequestItem]:
    return [
        V0GetNormQueryBidsRequestItem(advert_id=advert_id, nm_id=nmid)
        for nmid in nmids
    ]
