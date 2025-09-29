__all__ = ("MinCpmMixin",)

from app.core.wb_api.data_classes.advs.bid_payment_types import BidPaymentType
from app.core.wb_api.data_classes.advs.min_cpm import PlacementType, BidsData
from app.core.wb_api.http_request import try_except_decorator, requests
from ..protocols import WBAPIProtocol

"""Data Exemple:
             "advert_id": 98765432,
             "nm_ids": [
             12345678,
             87654321
             ],
             "payment_type": "cpm",
             "placement_types": [
             "combined",
             "search",
             "recommendation"
             ]
             }


 """


class MinCpmMixin:
    @try_except_decorator(20, 60)
    async def get_min_cpm_for_adv(
        self: WBAPIProtocol, adv_id: int, nmids: list[int], payment_type: BidPaymentType
    ) -> BidsData:
        url = "https://advert-api.wildberries.ru/adv/v0/bids/min"

        data = {
            "advert_id": adv_id,
            "nm_ids": nmids,
            "payment_type": payment_type.CPM.value,
            "placement_types": [
                PlacementType.SEARCH.value,
                PlacementType.RECOMMENDATION.value,
                PlacementType.COMBINED.value,
            ],
        }

        result_data = await requests(self.session, "POST", url, data=data)
        bids_data = BidsData.model_validate(result_data)
        return bids_data
