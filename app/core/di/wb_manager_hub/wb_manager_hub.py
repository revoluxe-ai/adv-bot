import typing

from dependency_injector.providers import Provider

if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.managers import WBDataManager, WBModifier
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager import UpdateClusterBidsManager
    from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager import \
        RedisKeywordBidderStatusManager
    from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager import WBManager

WBManagerProvider = Provider["WBManager"]


class WBManagerHub:
    def __init__(
        self,
        wb_data_manager: "WBDataManager",
        wb_promotion_manager: "WBModifier",
        wb_manager: "WBManager | WBManagerProvider",
        redis_client_wrapper: "RedisClient",
        cluster_bids_update_manager: "UpdateClusterBidsManager",
        redis_keyword_bidder_status_manager: "RedisKeywordBidderStatusManager",
    ):
        self.__wb_data_manager = wb_data_manager
        self.__wb_promotion_manager = wb_promotion_manager
        if isinstance(wb_manager, Provider):
            resolved_wb_manager = wb_manager()
        else:
            resolved_wb_manager = wb_manager
        self.__wb_manager = resolved_wb_manager
        self.__redis_client_wrapper = redis_client_wrapper
        self.__cluster_bids_update_manager = cluster_bids_update_manager
        self.__redis_keyword_bidder_status_manager = redis_keyword_bidder_status_manager

    @property
    def redis_keyword_bidder_status_manager(self) -> "RedisKeywordBidderStatusManager":
        return self.__redis_keyword_bidder_status_manager

    @property
    def cluster_bids_update_manager(self) -> "UpdateClusterBidsManager":
        return self.__cluster_bids_update_manager


    @property
    def wb_data_manager(self) -> "WBDataManager":
        return self.__wb_data_manager

    @property
    def wb_modifier(self) -> "WBModifier":
        return self.__wb_promotion_manager

    @property
    def redis_client_wrapper(self) -> "RedisClient":
        return self.__redis_client_wrapper

    @property
    def wb_manager(self) -> "WBManager":
        return self.__wb_manager
