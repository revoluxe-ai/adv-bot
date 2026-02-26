from dataclasses import dataclass
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.dto.bidder_update_data import \
    BidderUpdateData
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.mappers.adv_id_item_map import \
    AdvIdItemCalculateData


@dataclass(frozen=True)
class BidderCalculateData:
    data_from_local: set[AdvIdItemCalculateData]
    data_from_wb_api: BidderUpdateData
    # Per-adv value can be None (e.g. when individual_keywords_target_place_mode is False)
    predict_bids_data: (
        dict[int, (dict[int, dict[str, dict[int, int]]] | None)] | None
    )
