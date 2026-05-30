from dependency_injector import containers, providers

from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager import (
    RedisKeywordBidderStatusManager,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager import (
    UpdateClusterBidsManager,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager import (
    WBManager,
)
from app.modules.cluster_bids_redis import (
    RedisApiClusterBidsManager,
    RedisClusterBidsManager,
    RedisClusterBidsTimestampManager,
)


class ClusterBidsManagerContainer(containers.DeclarativeContainer):
    shop_id = providers.Dependency(instance_of=str)
    redis_client = providers.Dependency()
    tasks_manager = providers.Dependency(instance_of=TasksManager)

    # Контейнер создаётся под конкретный shop_id, поэтому держим один экземпляр
    wb_manager: providers.Singleton[WBManager] = providers.Singleton(
        WBManager, shop_id=shop_id
    )
    redis_keyword_bidder_status_manager: providers.Singleton[
        RedisKeywordBidderStatusManager
    ] = providers.Singleton(
        RedisKeywordBidderStatusManager, redis_client=redis_client
    )
    redis_cluster_bids_manager: providers.Singleton[
        RedisClusterBidsManager
    ] = providers.Singleton(RedisClusterBidsManager, redis_client=redis_client)
    redis_api_cluster_bids_manager: providers.Singleton[
        RedisApiClusterBidsManager
    ] = providers.Singleton(RedisApiClusterBidsManager, redis_client=redis_client)
    redis_cluster_bids_timestamp_manager: providers.Singleton[
        RedisClusterBidsTimestampManager
    ] = providers.Singleton(
        RedisClusterBidsTimestampManager, redis_client=redis_client
    )
    update_cluster_bids_manager: providers.Factory[UpdateClusterBidsManager] = (
        providers.Factory(
            UpdateClusterBidsManager,
            wb_manager=wb_manager,
            redis_keyword_bidder_status_manager=redis_keyword_bidder_status_manager,
            redis_cluster_bids_manager=redis_cluster_bids_manager,
            redis_api_cluster_bids_manager=redis_api_cluster_bids_manager,
            redis_cluster_bids_timestamp_manager=redis_cluster_bids_timestamp_manager,
            tasks_manager=tasks_manager,
        )
    )

