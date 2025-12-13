
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.mappers.adv_id_item_map import \
    AdvIdItemCalculateData


class CurrentPositionMapper:

    @staticmethod
    def get_current_position(map_data: AdvIdItemCalculateData) -> float:
        return map_data.current_position



